from buildbot.process import factory
from buildbot.steps import source, shell, transfer, master
from buildbot.status.builder import SUCCESS
from buildbot.process.properties import WithProperties
from buildbot import locks
from pypybuildbot.util import symlink_force
import os

# buildbot supports SlaveLocks, which can be used to limit the amout of builds
# to be run on each slave in parallel.  However, they assume that each
# buildslave is on a differen physical machine, which is not the case for
# tannit32 and tannit64.  As a result, we have to use a global lock, and
# manually tell each builder that uses tannit to acquire it.
#
# Look at the various "locks" session in master.py/BuildmasterConfig.  For
# benchmarks, the locks is aquired for the single steps: this way we can run
# translations in parallel, but then the actual benchmarks are run in
# sequence.

# there are 8 logical CPUs, but only 4 physical ones
TannitCPU = locks.MasterLock('tannit_cpu', maxCount=6)
SpeedPythonCPU = locks.MasterLock('speed_python_cpu', maxCount=24)


class ShellCmd(shell.ShellCommand):
    # our own version that can distinguish abort cases (rc == -1)

    def getText(self, cmd, results):
        if cmd is not None and cmd.rc == -1:
            return self.describe(True) + ['aborted']
        return shell.ShellCommand.getText(self, cmd, results)

class PyPyUpload(transfer.FileUpload):
    parms = transfer.FileUpload.parms + ['basename']

    def start(self):
        properties = self.build.getProperties()
        branch = properties['branch']
        if branch is None:
            branch = 'trunk'
        #masterdest = properties.render(self.masterdest)
        masterdest = os.path.expanduser(self.masterdest)
        if branch.startswith('/'):
            branch = branch[1:]
        # workaround for os.path.join
        masterdest = os.path.join(masterdest, branch)
        if not os.path.exists(masterdest):
            os.makedirs(masterdest)
        #
        assert '%(final_file_name)s' in self.basename
        symname = self.basename.replace('%(final_file_name)s', 'latest')
        assert '%' not in symname
        self.symlinkname = os.path.join(masterdest, symname)
        #
        basename = WithProperties(self.basename).getRenderingFor(self.build)
        self.masterdest = os.path.join(masterdest, basename)
        #
        transfer.FileUpload.start(self)

    def finished(self, *args, **kwds):
        transfer.FileUpload.finished(self, *args, **kwds)
        try:
            os.chmod(self.masterdest, 0644)
        except OSError:
            pass
        try:
            symlink_force(os.path.basename(self.masterdest), self.symlinkname)
        except OSError:
            pass

class Translate(ShellCmd):
    name = "translate"
    description = ["translating"]
    descriptionDone = ["translation"]

    command = ["translate.py", "--batch"]
    translationTarget = "targetpypystandalone"
    haltOnFailure = True

    def __init__(self, translationArgs, targetArgs,
                 workdir="build/pypy/translator/goal",
                 interpreter='pypy',
                 *a, **kw):
        add_args = {'translationArgs': translationArgs,
                    'targetArgs': targetArgs,
                    'interpreter': interpreter}
        kw['timeout'] = 7200
        ShellCmd.__init__(self, workdir, *a, **kw)
        self.addFactoryArguments(**add_args)
        self.command = ([interpreter] + self.command + translationArgs +
                        [self.translationTarget] + targetArgs)
        #self.command = ['cp', '/tmp/pypy-c', '.']


class PytestCmd(ShellCmd):

    def commandComplete(self, cmd):
        from pypybuildbot.summary import RevisionOutcomeSet
        if 'pytestLog' not in cmd.logs:
            return
        pytestLog = cmd.logs['pytestLog']
        outcome = RevisionOutcomeSet(None)
        outcome.populate(pytestLog)
        summary = outcome.get_summary()
        build_status = self.build.build_status
        builder = build_status.builder
        properties = build_status.getProperties()
        if not hasattr(builder, 'summary_by_branch_and_revision'):
            builder.summary_by_branch_and_revision = {}
        try:
            rev = properties['got_revision']
            branch = properties['branch']
            if branch is None:
                branch = 'trunk'
            if branch.endswith('/'):
                branch = branch[:-1]
        except KeyError:
            return
        else:
            d = builder.summary_by_branch_and_revision
            key = (branch, rev)
            if key in d:
                summary += d[key]
            d[key] = summary
        builder.saveYourself()

# ________________________________________________________________

class UpdateCheckout(ShellCmd):
    description = 'hg update'
    command = 'UNKNOWN'

    def start(self):
        properties = self.build.getProperties()
        branch = properties['branch']
        command = ["hg", "update", "--clean", "-r", branch or 'default']
        self.setCommand(command)
        ShellCmd.start(self)

class CheckGotRevision(ShellCmd):
    description = 'got_revision'
    command = ['hg', 'parents', '--template', '{rev}:{node}']

    def commandComplete(self, cmd):
        if cmd.rc == 0:
            got_revision = cmd.logs['stdio'].getText()
            # manually get the effect of {node|short} without using a
            # '|' in the command-line, because it doesn't work on Windows
            num = got_revision.find(':')
            if num > 0:
                got_revision = got_revision[:num+13]
            #
            final_file_name = got_revision.replace(':', '-')
            # ':' should not be part of filenames --- too many issues
            self.build.setProperty('got_revision', got_revision, 'got_revision')
            self.build.setProperty('final_file_name', final_file_name, 'got_revision')

def update_hg(platform, factory, repourl, workdir, use_branch):
    if platform == 'win32':
        command = "if not exist .hg rmdir /q /s ."
    else:
        command = "if [ ! -d .hg ]; then rm -fr * .[a-z]*; fi"
    factory.addStep(ShellCmd(description="rmdir?",
                             command = command,
                             workdir = workdir,
                             haltOnFailure=False))
    #
    if platform == "win32":
        command = "if not exist .hg %s"
    else:
        command = "if [ ! -d .hg ]; then %s; fi"
    command = command % ("hg clone -U " + repourl + " .")
    factory.addStep(ShellCmd(description="hg clone",
                             command = command,
                             workdir = workdir,
                             haltOnFailure=True))
    #
    factory.addStep(ShellCmd(description="hg purge",
                             command = "hg --config extensions.purge= purge --all",
                             workdir = workdir,
                             haltOnFailure=True))
    #
    factory.addStep(ShellCmd(description="hg pull",
                             command = "hg pull",
                             workdir = workdir))
    #
    if use_branch:
        factory.addStep(UpdateCheckout(workdir = workdir,
                                       haltOnFailure=True))
    else:
        factory.addStep(ShellCmd(description="hg update",
                                 command = "hg update --clean",
                                 workdir = workdir))

def setup_steps(platform, factory, workdir=None):
    # XXX: this assumes that 'hg' is in the path
    import getpass
    repourl = 'https://bitbucket.org/pypy/pypy/'
    if getpass.getuser() == 'antocuni':
        # for debugging
        repourl = '/home/antocuni/pypy/default'
    #
    update_hg(platform, factory, repourl, workdir, use_branch=True)
    #
    factory.addStep(CheckGotRevision(workdir=workdir))


class Own(factory.BuildFactory):

    def __init__(self, platform='linux', cherrypick='', extra_cfgs=[]):
        factory.BuildFactory.__init__(self)

        setup_steps(platform, self)

        self.addStep(PytestCmd(
            description="pytest",
            command=["python", "testrunner/runner.py",
                     "--logfile=testrun.log",
                     "--config=pypy/testrunner_cfg.py",
                     "--config=~/machine_cfg.py",
                     "--root=pypy", "--timeout=10800"
                     ] + ["--config=%s" % cfg for cfg in extra_cfgs],
            logfiles={'pytestLog': 'testrun.log'},
            timeout = 4000,
            env={"PYTHONPATH": ['.'],
                 "PYPYCHERRYPICK": cherrypick}))

class Translated(factory.BuildFactory):

    def __init__(self, platform='linux',
                 translationArgs=['-O2'], targetArgs=[],
                 app_tests=False,
                 interpreter='pypy',
                 lib_python=False,
                 pypyjit=False
                 ):
        factory.BuildFactory.__init__(self)

        setup_steps(platform, self)

        self.addStep(Translate(translationArgs, targetArgs,
                               interpreter=interpreter))

        if app_tests:
            if app_tests == True:
                app_tests = []
            self.addStep(PytestCmd(
                description="app-level (-A) test",
                command=["python", "testrunner/runner.py",
                         "--logfile=pytest-A.log",
                         "--config=pypy/pytest-A.cfg",
                         "--root=pypy", "--timeout=1800"
                         ] + ["--config=%s" % cfg for cfg in app_tests],
                logfiles={'pytestLog': 'pytest-A.log'},
                timeout = 4000,
                env={"PYTHONPATH": ['.']}))

        if lib_python:
            self.addStep(PytestCmd(
                description="lib-python test",
                command=["python", "pypy/test_all.py",
                         "--pypy=pypy/translator/goal/pypy-c",
                         "--resultlog=cpython.log", "lib-python"],
                logfiles={'pytestLog': 'cpython.log'}))

        if pypyjit:
            # kill this step when the transition to test_pypy_c_new has been
            # completed
            # "old" test_pypy_c
            self.addStep(PytestCmd(
                description="pypyjit tests",
                command=["python", "pypy/test_all.py",
                         "--pypy=pypy/translator/goal/pypy-c",
                         "--resultlog=pypyjit.log",
                         "pypy/module/pypyjit/test"],
                logfiles={'pytestLog': 'pypyjit.log'}))
            #
            # "new" test_pypy_c
            self.addStep(PytestCmd(
                description="pypyjit tests",
                command=["pypy/translator/goal/pypy-c", "pypy/test_all.py",
                         "--resultlog=pypyjit_new.log",
                         "pypy/module/pypyjit/test_pypy_c"],
                logfiles={'pytestLog': 'pypyjit_new.log'}))

        if pypyjit:
            kind = 'jit'
        else:
            if '--stackless' in translationArgs:
                kind = 'stackless'
            elif '-Ojit' in translationArgs:
                kind = 'jitnojit'
            elif '-O2' in translationArgs:
                kind = 'nojit'
            else:
                kind = 'unknown'
        name = 'pypy-c-' + kind + '-%(final_file_name)s-' + platform
        self.addStep(ShellCmd(
            description="compress pypy-c",
            command=["python", "pypy/tool/release/package.py",
                     ".", WithProperties(name), 'pypy',
                     '.'],
            workdir='build'))
        nightly = '~/nightly/'
        if platform == "win32":
            extension = ".zip"
        else:
            extension = ".tar.bz2"
        pypy_c_rel = "build/" + name + extension
        self.addStep(PyPyUpload(slavesrc=WithProperties(pypy_c_rel),
                                masterdest=WithProperties(nightly),
                                basename=name + extension,
                                workdir='.',
                                blocksize=100*1024))

class JITBenchmark(factory.BuildFactory):
    def __init__(self, platform='linux', host='tannit', postfix=None):
        factory.BuildFactory.__init__(self)

        setup_steps(platform, self)
        #
        repourl = 'https://bitbucket.org/pypy/benchmarks'
        update_hg(platform, self, repourl, 'benchmarks', use_branch=False)
        #
        if host == 'tannit':
            lock = TannitCPU
        elif host == 'speed_python':
            lock = SpeedPythonCPU
        else:
            assert False, 'unknown host %s' % host
        #
        self.addStep(
            Translate(
                translationArgs=['-Ojit'],
                targetArgs=[],
                haltOnFailure=True,
                # this step can be executed in parallel with other builds
                locks=[lock.access('counting')],
                )
            )
        pypy_c_rel = "../build/pypy/translator/goal/pypy-c"
        if postfix:
            addopts = ['--postfix', postfix]
        else:
            addopts = []
        self.addStep(ShellCmd(
            # this step needs exclusive access to the CPU
            locks=[TannitCPU.access('exclusive')],
            description="run benchmarks on top of pypy-c",
            command=["python", "runner.py", '--output-filename', 'result.json',
                    '--pypy-c', pypy_c_rel,
                     '--baseline', pypy_c_rel,
                     '--args', ',--jit off',
                     '--upload',
                     '--revision', WithProperties('%(got_revision)s'),
                     '--branch', WithProperties('%(branch)s'),
                     ] + addopts,
            workdir='./benchmarks',
            timeout=3600))
        # a bit obscure hack to get both os.path.expand and a property
        filename = '%(got_revision)s' + (postfix or '')
        resfile = os.path.expanduser("~/bench_results/%s.json" % filename)
        self.addStep(transfer.FileUpload(slavesrc="benchmarks/result.json",
                                         masterdest=WithProperties(resfile),
                                         workdir="."))
