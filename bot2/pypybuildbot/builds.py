from buildbot.process import factory
from buildbot.steps import shell, transfer
from buildbot.steps.trigger import Trigger
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

# there are 8 logical CPUs, but only 4 physical ones, and only enough memory for ~3 translations
TannitCPU = locks.MasterLock('tannit_cpu', maxCount=3)
SpeedPythonCPU = locks.MasterLock('speed_python_cpu', maxCount=24)
#WinLockCPU = locks.MasterLock('win_cpu', maxCount=1)

# The cross translation machine can accomodate 2 jobs at the same time
ARMCrossLock = locks.MasterLock('arm_cpu', maxCount=2)
# while the boards can only run one job at the same time
ARMBoardLock = locks.SlaveLock('arm_boards', maxCount=1)


# XXX monkey patch Trigger class, there are to issues with the list of renderables
# original: Trigger.renderables = [ 'set_propetries', 'scheduler', 'sourceStamp' ]
Trigger.renderables = [ 'set_properties', 'schedulerNames', 'sourceStamp' ]

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

class PyPyDownload(transfer.FileDownload):
    parms = transfer.FileDownload.parms + ['basename']

    def start(self):

        properties = self.build.getProperties()
        branch = properties['branch']
        revision = properties['revision']

        if branch is None:
            branch = 'trunk'
        mastersrc = os.path.expanduser(self.mastersrc)

        if branch.startswith('/'):
            branch = branch[1:]
        mastersrc = os.path.join(mastersrc, branch)
        if revision is not None:
            basename = WithProperties(self.basename).getRenderingFor(self.build)
            basename = basename.replace(':', '-')
        else:
            basename = self.basename.replace('%(revision)s', 'latest')
            assert '%' not in basename

        self.mastersrc = os.path.join(mastersrc, basename)
        #
        transfer.FileDownload.start(self)

class NumpyStatusUpload(transfer.FileUpload):
    def finished(self, *args, **kwds):
        transfer.FileUpload.finished(self, *args, **kwds)
        try:
            os.chmod(self.masterdest, 0644)
        except OSError:
            pass
        try:
            symname = os.path.join(os.path.dirname(self.masterdest),
                                   'latest.html')
            symlink_force(self.masterdest, symname)
        except OSError:
            pass

class Translate(ShellCmd):
    name = "translate"
    description = ["translating"]
    descriptionDone = ["translation"]

    command = ["../../rpython/bin/rpython", "--batch"]
    translationTarget = "targetpypystandalone"
    haltOnFailure = True

    def __init__(self, translationArgs, targetArgs,
                 workdir="build/pypy/goal",
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

# _______________________________________________________________

class UpdateCheckout(ShellCmd):
    description = 'hg update'
    command = 'UNKNOWN'

    def __init__(self, workdir=None, haltOnFailure=True, force_branch=None,
                 **kwargs):
        ShellCmd.__init__(self, workdir=workdir, haltOnFailure=haltOnFailure,
                          **kwargs)
        self.force_branch = force_branch
        self.addFactoryArguments(force_branch=force_branch)

    def start(self):
        if self.force_branch is not None:
            branch = self.force_branch
            # Note: We could add a warning to the output if we
            # ignore the branch set by the user.
        else:
            properties = self.build.getProperties()
            branch = properties['branch'] or 'default'
        command = ["hg", "update", "--clean", "-r", branch]
        self.setCommand(command)
        ShellCmd.start(self)


class CheckGotRevision(ShellCmd):
    description = 'got_revision'
    command = ['hg', 'parents', '--template', 'got_revision:{rev}:{node}']

    def commandComplete(self, cmd):
        if cmd.rc == 0:
            got_revision = cmd.logs['stdio'].getText()
            got_revision = got_revision.split('got_revision:')[-1]
            # manually get the effect of {node|short} without using a
            # '|' in the command-line, because it doesn't work on Windows
            num = got_revision.find(':')
            if num > 0:
                got_revision = got_revision[:num + 13]
            #
            final_file_name = got_revision.replace(':', '-')
            # ':' should not be part of filenames --- too many issues
            self.build.setProperty('got_revision', got_revision,
                                   'got_revision')
            self.build.setProperty('final_file_name', final_file_name,
                                   'got_revision')


def update_hg(platform, factory, repourl, workdir, use_branch,
              force_branch=None):
    if platform == 'win32':
        command = "if not exist .hg rmdir /q /s ."
    else:
        command = "if [ ! -d .hg ]; then rm -fr * .[a-z]*; fi"
    factory.addStep(ShellCmd(description="rmdir?",
                             command=command,
                             workdir=workdir,
                             haltOnFailure=False))
    #
    if platform == "win32":
        command = "if not exist .hg %s"
    else:
        command = "if [ ! -d .hg ]; then %s; fi"
    command = command % ("hg clone -U " + repourl + " .")
    factory.addStep(ShellCmd(description="hg clone",
                             command=command,
                             workdir=workdir,
                             timeout=3600,
                             haltOnFailure=True))
    #
    factory.addStep(
        ShellCmd(description="hg purge",
                 command="hg --config extensions.purge= purge --all",
                 workdir=workdir,
                 haltOnFailure=True))
    #
    factory.addStep(ShellCmd(description="hg pull",
                             command="hg pull",
                             workdir=workdir))
    #
    if use_branch or force_branch:
        factory.addStep(UpdateCheckout(workdir=workdir,
                                       haltOnFailure=True,
                                       force_branch=force_branch))
    else:
        factory.addStep(ShellCmd(description="hg update",
                command=WithProperties("hg update --clean %(revision)s"),
                workdir=workdir))


def setup_steps(platform, factory, workdir=None,
                repourl='https://bitbucket.org/pypy/pypy/',
                force_branch=None):
    # XXX: this assumes that 'hg' is in the path
    import getpass
    if getpass.getuser() == 'antocuni':
        # for debugging
        repourl = '/home/antocuni/pypy/default'
    #
    update_hg(platform, factory, repourl, workdir, use_branch=True,
              force_branch=force_branch)
    #
    factory.addStep(CheckGotRevision(workdir=workdir))

def build_name(platform, jit=False, flags=[], placeholder=None):
    if placeholder is None:
        placeholder = '%(final_file_name)s'
    if jit or '-Ojit' in flags:
        kind = 'jit'
    else:
        if '--stackless' in flags:
            kind = 'stackless'
        elif '-Ojit' in flags:
            kind = 'jitnojit'
        elif '-O2' in flags:
            kind = 'nojit'
        else:
            kind = 'unknown'
    return 'pypy-c-' + kind + '-%s-' % (placeholder,) + platform


def get_extension(platform):
    if platform == "win32":
        return ".zip"
    else:
        return ".tar.bz2"

def add_translated_tests(factory, prefix, platform, app_tests, lib_python, pypyjit):
    if app_tests:
        if app_tests == True:
            app_tests = []
        factory.addStep(PytestCmd(
            description="app-level (-A) test",
            command=prefix + ["python", "testrunner/runner.py",
                     "--logfile=pytest-A.log",
                     "--config=pypy/pytest-A.cfg",
                     "--root=pypy", "--timeout=3600"
                     ] + ["--config=%s" % cfg for cfg in app_tests],
            logfiles={'pytestLog': 'pytest-A.log'},
            timeout=4000,
            env={"PYTHONPATH": ['.']}))

    if lib_python:
        factory.addStep(PytestCmd(
            description="lib-python test",
            command=prefix + ["python", "pypy/test_all.py",
                     "--pypy=pypy/goal/pypy-c",
                     "--timeout=3600",
                     "--resultlog=cpython.log", "lib-python"],
            timeout=4000,
            logfiles={'pytestLog': 'cpython.log'}))

    if pypyjit:
        # kill this step when the transition to test_pypy_c_new has been
        # completed
        # "old" test_pypy_c
        factory.addStep(PytestCmd(
            description="pypyjit tests",
            command=prefix + ["python", "pypy/test_all.py",
                     "--pypy=pypy/goal/pypy-c",
                     "--resultlog=pypyjit.log",
                     "pypy/module/pypyjit/test"],
            logfiles={'pytestLog': 'pypyjit.log'}))
        #
        # "new" test_pypy_c
        if platform == 'win32':
            cmd = r'pypy\goal\pypy-c'
        else:
            cmd = 'pypy/goal/pypy-c'
        factory.addStep(PytestCmd(
            description="pypyjit tests",
            command=prefix + [cmd, "pypy/test_all.py",
                     "--resultlog=pypyjit_new.log",
                     "pypy/module/pypyjit/test_pypy_c"],
            logfiles={'pytestLog': 'pypyjit_new.log'}))

# ----

class Own(factory.BuildFactory):

    def __init__(self, platform='linux', cherrypick='', extra_cfgs=[], **kwargs):
        factory.BuildFactory.__init__(self)

        setup_steps(platform, self)

        timeout=kwargs.get('timeout', 4000)
        self.addStep(PytestCmd(
            description="pytest pypy",
            command=["python", "testrunner/runner.py",
                     "--logfile=testrun.log",
                     "--config=pypy/testrunner_cfg.py",
                     "--config=~/machine_cfg.py",
                     "--root=pypy", "--timeout=%s" % (timeout,)
                     ] + ["--config=%s" % cfg for cfg in extra_cfgs],
            logfiles={'pytestLog': 'testrun.log'},
            timeout=timeout,
            env={"PYTHONPATH": ['.'],
                 "PYPYCHERRYPICK": cherrypick}))

        self.addStep(PytestCmd(
            description="pytest rpython",
            command=["python", "testrunner/runner.py",
                     "--logfile=testrun.log",
                     "--config=pypy/testrunner_cfg.py",
                     "--config=~/machine_cfg.py",
                     "--root=rpython", "--timeout=%s" % (timeout,)
                     ] + ["--config=%s" % cfg for cfg in extra_cfgs],
            logfiles={'pytestLog': 'testrun.log'},
            timeout=timeout,
            env={"PYTHONPATH": ['.'],
                 "PYPYCHERRYPICK": cherrypick}))


class Translated(factory.BuildFactory):

    def __init__(self, platform='linux',
                 translationArgs=['-O2'], targetArgs=[],
                 app_tests=False,
                 interpreter='pypy',
                 lib_python=False,
                 pypyjit=False,
                 prefix=None
                 ):
        factory.BuildFactory.__init__(self)
        if prefix is not None:
            prefix = prefix.split()
        else:
            prefix = []

        setup_steps(platform, self)

        self.addStep(Translate(translationArgs, targetArgs,
                               interpreter=interpreter))

        add_translated_tests(self, prefix, platform, app_tests, lib_python, pypyjit)

        name = build_name(platform, pypyjit, translationArgs)
        self.addStep(ShellCmd(
            description="compress pypy-c",
            command=prefix + ["python", "pypy/tool/release/package.py",
                     ".", WithProperties(name), 'pypy',
                     '.'],
            workdir='build'))
        nightly = '~/nightly/'
        extension = get_extension(platform)
        pypy_c_rel = "build/" + name + extension
        self.addStep(PyPyUpload(slavesrc=WithProperties(pypy_c_rel),
                                masterdest=WithProperties(nightly),
                                basename=name + extension,
                                workdir='.',
                                blocksize=100 * 1024))


class TranslatedTests(factory.BuildFactory):
    '''
    Download a pypy nightly build and run the app-level tests on the binary
    '''

    def __init__(self, platform='linux',
                 app_tests=False,
                 lib_python=False,
                 pypyjit=False,
                 prefix=None,
                 translationArgs=[]
                 ):
        factory.BuildFactory.__init__(self)
        if prefix is not None:
            prefix = prefix.split()
        else:
            prefix = []

        # XXX extend to checkout the specific revision of the build
        setup_steps(platform, self)

        # download corresponding nightly build
        self.addStep(ShellCmd(
            description="Clear pypy-c",
            command=['rm', '-rf', 'pypy-c'],
            workdir='.'))
        extension = get_extension(platform)
        name = build_name(platform, pypyjit, translationArgs, placeholder='%(revision)s') + extension
        self.addStep(PyPyDownload(
            basename=name,
            mastersrc='~/nightly',
            slavedest='pypy_build' + extension,
            workdir='pypy-c'))

        # extract downloaded file
        if platform.startswith('win'):
            raise NotImplementedError
        else:
            self.addStep(ShellCmd(
                description="decompress pypy-c",
                command=['tar', '--extract', '--file=pypy_build'+ extension, '--strip-components=1', '--directory=.'],
                workdir='pypy-c'))

        # copy pypy-c to the expected location within the pypy source checkout
        self.addStep(ShellCmd(
            description="move pypy-c",
            command=['cp', '-v', 'pypy-c/bin/pypy', 'build/pypy/goal/pypy-c'],
            workdir='.'))
        # copy generated and copied header files to build/include
        self.addStep(ShellCmd(
            description="move header files",
            command=['cp', '-vr', 'pypy-c/include', 'build'],
            workdir='.'))
        # copy ctypes_resource_cache generated during translation
        self.addStep(ShellCmd(
            description="move ctypes resource cache",
            command=['cp', '-rv', 'pypy-c/lib_pypy/ctypes_config_cache', 'build/lib_pypy'],
            workdir='.'))

        add_translated_tests(self, prefix, platform, app_tests, lib_python, pypyjit)


class NightlyBuild(factory.BuildFactory):
    def __init__(self, platform='linux',
                 translationArgs=['-O2'], targetArgs=[],
                 interpreter='pypy',
                 prefix=[],
                 trigger=None,
                 ):
        factory.BuildFactory.__init__(self)

        setup_steps(platform, self)

        self.addStep(Translate(translationArgs, targetArgs,
                               interpreter=interpreter))
        name = build_name(platform, flags=translationArgs)
        self.addStep(ShellCmd(
            description="compress pypy-c",
            command=prefix + ["python", "pypy/tool/release/package.py",
                     ".", WithProperties(name), 'pypy',
                     '.'],
            workdir='build'))
        nightly = '~/nightly/'
        extension = get_extension(platform)
        pypy_c_rel = "build/" + name + extension
        self.addStep(PyPyUpload(slavesrc=WithProperties(pypy_c_rel),
                                masterdest=WithProperties(nightly),
                                basename=name + extension,
                                workdir='.',
                                blocksize=100 * 1024))
        if trigger: # if provided trigger schedulers that are depend on this one
            self.addStep(Trigger(schedulerNames=[trigger]))


class JITBenchmark(factory.BuildFactory):
    def __init__(self, platform='linux', host='tannit', postfix=''):
        factory.BuildFactory.__init__(self)

        setup_steps(platform, self)
        #
        repourl = 'https://bitbucket.org/pypy/benchmarks'
        update_hg(platform, self, repourl, 'benchmarks', use_branch=False)
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
        if host == 'tannit':
            pypy_c_rel = 'build/pypy/goal/pypy-c'
            self.addStep(ShellCmd(
                env={'PYTHONPATH': './benchmarks/lib/jinja2'},
                description="measure numpy compatibility",
                command=[pypy_c_rel,
                         'build/pypy/module/micronumpy/tool/numready/',
                         pypy_c_rel, 'numpy-compat.html'],
                workdir="."))
            resfile = os.path.expanduser("~/numpy_compat/%(got_revision)s.html")
            self.addStep(NumpyStatusUpload(
                slavesrc="numpy-compat.html",
                masterdest=WithProperties(resfile),
                workdir="."))
        pypy_c_rel = "../build/pypy/goal/pypy-c"
        self.addStep(ShellCmd(
            # this step needs exclusive access to the CPU
            locks=[lock.access('exclusive')],
            description="run benchmarks on top of pypy-c",
            command=["python", "runner.py", '--output-filename', 'result.json',
                     '--niceness', '0',  # can't get limits.conf to allow -10
                     '--changed', pypy_c_rel,
                     '--baseline', pypy_c_rel,
                     '--args', ',--jit off',
                     '--upload',
                     '--upload-executable', 'pypy-c' + postfix,
                     '--upload-project', 'PyPy',
                     '--revision', WithProperties('%(got_revision)s'),
                     '--branch', WithProperties('%(branch)s'),
                     '--upload-urls', 'http://speed.pypy.org/',
                     '--upload-baseline',
                     '--upload-baseline-executable', 'pypy-c-jit' + postfix,
                     '--upload-baseline-project', 'PyPy',
                     '--upload-baseline-revision',
                     WithProperties('%(got_revision)s'),
                     '--upload-baseline-branch', WithProperties('%(branch)s'),
                     '--upload-baseline-urls', 'http://speed.pypy.org/',
                     ],
            workdir='./benchmarks',
            timeout=3600))
        # a bit obscure hack to get both os.path.expand and a property
        filename = '%(got_revision)s' + (postfix or '')
        resfile = os.path.expanduser("~/bench_results/%s.json" % filename)
        self.addStep(transfer.FileUpload(slavesrc="benchmarks/result.json",
                                         masterdest=WithProperties(resfile),
                                         workdir="."))


class CPythonBenchmark(factory.BuildFactory):
    '''
    Check out and build CPython and run the benchmarks with it.

    This will overwrite the branch even if it was specified
    in the buildbot webinterface!
    '''
    def __init__(self, branch, platform='linux64'):
        '''
        branch: The branch of cpython that will be used.
        '''
        factory.BuildFactory.__init__(self)

        # checks out and updates the repo
        setup_steps(platform, self, repourl='http://hg.python.org/cpython',
                    force_branch=branch)

        # check out and update benchmarks
        repourl = 'https://bitbucket.org/pypy/benchmarks'
        update_hg(platform, self, repourl, 'benchmarks', use_branch=False)

        lock = SpeedPythonCPU

        self.addStep(ShellCmd(
            description="configure cpython",
            command=["./configure"],
            timeout=300,
            haltOnFailure=True))

        self.addStep(ShellCmd(
            description="cleanup cpython",
            command=["make", "clean"],
            timeout=300))

        self.addStep(ShellCmd(
            description="make cpython",
            command=["make"],
            timeout=600,
            haltOnFailure=True))

        self.addStep(ShellCmd(
            description="test cpython",
            command=["make", "buildbottest"],
            haltOnFailure=False,
            warnOnFailure=True,
            timeout=600))

        cpython_interpreter = '../build/python'
        self.addStep(ShellCmd(
            # this step needs exclusive access to the CPU
            locks=[lock.access('exclusive')],
            description="run benchmarks on top of cpython",
            command=["python", "runner.py", '--output-filename', 'result.json',
                     '--changed', cpython_interpreter,
                     '--baseline', './nullpython.py',
                     '--upload',
                     '--upload-project', 'cpython',
                     '--upload-executable', 'cpython2',
                     '--revision', WithProperties('%(got_revision)s'),
                     '--branch', WithProperties('%(branch)s'),
                     '--upload-urls', 'http://localhost/',
                     ],
            workdir='./benchmarks',
            haltOnFailure=True,
            timeout=3600))

        # a bit obscure hack to get both os.path.expand and a property
        filename = '%(got_revision)s'
        resultfile = os.path.expanduser("~/bench_results/%s.json" % filename)
        self.addStep(transfer.FileUpload(slavesrc="benchmarks/result.json",
                                         masterdest=WithProperties(resultfile),
                                         workdir="."))
