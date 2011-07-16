from buildbot.process import factory
from buildbot.steps import source, shell, transfer, master
from buildbot.status.builder import SUCCESS
from buildbot.process.properties import WithProperties
from pypybuildbot.util import symlink_force
import os

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
        masterdest = properties.render(self.masterdest)
        masterdest = os.path.expanduser(masterdest)
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
        basename = WithProperties(self.basename).render(properties)
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

    command = ["pypy", "translate.py", "--batch"]
    translationTarget = "targetpypystandalone"
    haltOnFailure = True

    def __init__(self, translationArgs, targetArgs,
                 workdir="build/pypy/translator/goal",
                 *a, **kw):
        add_args = {'translationArgs': translationArgs,
                    'targetArgs': targetArgs}
        kw['timeout'] = 3600
        ShellCmd.__init__(self, workdir, *a, **kw)
        self.addFactoryArguments(**add_args)
        self.command = (self.command + translationArgs +
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

def setup_steps(platform, factory, workdir=None):
    # XXX: this assumes that 'hg' is in the path
    import getpass
    repourl = 'https://bitbucket.org/pypy/pypy/'
    if getpass.getuser() == 'antocuni':
        # for debugging
        repourl = '/home/antocuni/pypy/pypy-hg'
    #
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
    factory.addStep(UpdateCheckout(workdir = workdir,
                                   haltOnFailure=True))
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
                 lib_python=False,
                 pypyjit=False
                 ):
        factory.BuildFactory.__init__(self)

        setup_steps(platform, self)

        self.addStep(Translate(translationArgs, targetArgs))

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
            else:
                kind = 'nojit'
        name = 'pypy-c-' + kind + '-%(final_file_name)s-' + platform
        self.addStep(ShellCmd(
            description="compress pypy-c",
            command=["python", "pypy/tool/release/package.py",
                     ".", WithProperties(name), 'pypy',
                     '.'],
            workdir='build'))
        nightly = '~/nightly/'
        pypy_c_rel = "build/" + name + ".tar.bz2"
        self.addStep(PyPyUpload(slavesrc=WithProperties(pypy_c_rel),
                                masterdest=WithProperties(nightly),
                                basename=name + ".tar.bz2",
                                workdir='.',
                                blocksize=100*1024))

class JITBenchmark(factory.BuildFactory):
    def __init__(self, platform='linux'):
        factory.BuildFactory.__init__(self)

        setup_steps(platform, self)
        self.addStep(ShellCmd(description="checkout benchmarks",
            command=['svn', 'co', 'https://bitbucket.org/pypy/benchmarks/trunk',
                     'benchmarks'],
            workdir='.'))
        self.addStep(Translate(['-Ojit'], []))
        pypy_c_rel = "../build/pypy/translator/goal/pypy-c"
        self.addStep(ShellCmd(
            description="run benchmarks on top of pypy-c",
            command=["python", "runner.py", '--output-filename', 'result.json',
                    '--pypy-c', pypy_c_rel,
                     '--baseline', pypy_c_rel,
                     '--args', ',--jit off'
                     '--upload', #'--force-host', 'bigdog',
                     '--revision', WithProperties('%(got_revision)s'),
                     '--branch', WithProperties('%(branch)s')],
            workdir='./benchmarks',
            haltOnFailure=True))
        # a bit obscure hack to get both os.path.expand and a property
        resfile = os.path.expanduser("~/bench_results/%(got_revision)s.json")
        self.addStep(transfer.FileUpload(slavesrc="benchmarks/result.json",
                                         masterdest=WithProperties(resfile),
                                         workdir="."))

##        self.addStep(ShellCmd(
##            description="run on top of python with psyco",
##            command=["python", "runner.py", '--output-filename', 'result.json',
##                    '--pypy-c', 'psyco/python_with_psyco.sh',
##                     '--revision', WithProperties('%(got_revision)s'),
##                     '--upload', #'--force-host', 'bigdog',
##                     '--branch', WithProperties('%(branch)s'),
##                     ],
##            workdir='./benchmarks',
##            haltOnFailure=True))
