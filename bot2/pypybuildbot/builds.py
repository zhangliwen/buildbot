from buildbot.steps.source.mercurial import Mercurial
from buildbot.steps.source.git import Git
from buildbot.process.buildstep import BuildStep
from buildbot.process import factory
from buildbot.steps import shell, transfer
from buildbot.steps.trigger import Trigger
from buildbot.process.properties import WithProperties, Interpolate
from buildbot import locks
from pypybuildbot.util import symlink_force
from buildbot.status.results import SKIPPED, SUCCESS
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

# tannit has 8 logical CPUs, but only 4 physical ones, and memory for ~3 translations
TannitCPU = locks.MasterLock('tannit_cpu', maxCount=3)
SpeedPythonCPU = locks.MasterLock('speed_python_cpu', maxCount=24)
WinSlaveLock = locks.SlaveLock('win_cpu', maxCount=1)
# speed-old has 24 cores, but memory for ~2 translations
SpeedOldLock = locks.MasterLock('speed_old_lock', maxCount=2)


# The cross translation machine can accomodate 2 jobs at the same time
ARMCrossLock = locks.MasterLock('arm_cpu', maxCount=2)
# while the boards can only run one job at the same time
ARMBoardLock = locks.SlaveLock('arm_boards', maxCount=1)

map_branch_name = lambda x: x if x not in ['', None, 'default'] else 'trunk'

class ShellCmd(shell.ShellCommand):
    # our own version that can distinguish abort cases (rc == -1)

    def getText(self, cmd, results):
        if cmd is not None and cmd.rc == -1:
            return self.describe(True) + ['aborted']
        return shell.ShellCommand.getText(self, cmd, results)


class PyPyUpload(transfer.FileUpload):
    parms = transfer.FileUpload.parms + ['basename']
    haltOnFailure = False

    def start(self):
        properties = self.build.getProperties()
        branch = map_branch_name(properties['branch'])
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
        branch = map_branch_name(properties['branch'])
        revision = properties.getProperty('final_file_name')
        mastersrc = os.path.expanduser(self.mastersrc)

        if branch.startswith('/'):
            branch = branch[1:]
        mastersrc = os.path.join(mastersrc, branch)
        if revision:
            basename = WithProperties(self.basename).getRenderingFor(self.build)
            basename = basename.replace(':', '-')
        else:
            basename = self.basename.replace('%(final_file_name)s', 'latest')
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
            branch = map_branch_name(properties['branch'])
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

class SuccessAlways(ShellCmd):
    def evaluateCommand(self, cmd):
        return SUCCESS

# _______________________________________________________________
# XXX Currently the build properties got_revision and final_file_name contain
# the revision number and the changeset-id, CheckGotRevision takes care to set
# the corresponding build properties
# rev:changeset for got_revision
# rev-changeset for final_file_name
#
# The rev part of got_revision and filename is used everywhere to sort the
# builds, i.e. on the summary and download pages.
#
# The rev part is strictly local and needs to be removed from the SourceStamp,
# at least for decoupled builds, which is what ParseRevision does.
#
# XXX in general it would be nice to drop the revision-number using only the
# changeset-id for got_revision and final_file_name and sorting the builds
# chronologically

class UpdateGitCheckout(ShellCmd):
    description = 'git checkout'
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
        command = ["git", "checkout", "-f", branch]
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
            if not self.build.hasProperty('final_file_name'):
                self.build.setProperty('final_file_name', final_file_name,
                                       'got_revision')

class ParseRevision(BuildStep):
    """Parse the revision property of the source stamp and extract the global
    part of the revision
    123:3a34 -> 3a34"""
    name = "parse_revision"

    def __init__(self, *args, **kwargs):
        BuildStep.__init__(self, *args, **kwargs)

    @staticmethod
    def hideStepIf(results, step):
        return results==SKIPPED

    @staticmethod
    def doStepIf(step):
        revision = step.build.getSourceStamp().revision
        return isinstance(revision, (unicode, str)) and ':' in revision

    def start(self):
        stamp = self.build.getSourceStamp()
        revision = stamp.revision if stamp.revision is not None else ''
        #
        if not isinstance(revision, (unicode, str)) or ":" not in revision:
            self.finished(SKIPPED)
            return
        #
        self.build.setProperty('original_revision', revision, 'parse_revision')
        self.build.setProperty('final_file_name',
                                revision.replace(':', '-'), 'parse_revision')
        #
        parts = revision.split(':')
        self.build.setProperty('revision', parts[1], 'parse_revision')
        stamp.revision = parts[1]
        self.finished(SUCCESS)


# hack the Mercurial class in-place: it should do "hg pull" without
# passing a "--rev" argument.  The problem is that while it sounds like
# a good idea, passing a "--rev" argument here changes the order of
# the checkouts.  Then our revisions "12345:432bcbb1ba" are bogus.
def _my_pullUpdate(self, res):
    command = ['pull' , self.repourl]
    #if self.revision:                   <disabled!>
    #    command.extend(['--rev', self.revision])
    d = self._dovccmd(command)
    d.addCallback(self._checkBranchChange)
    return d
assert hasattr(Mercurial, '_pullUpdate')
Mercurial._pullUpdate = _my_pullUpdate


def update_hg_old_method(platform, factory, repourl, workdir):
    # baaaaaah.  Seems that the Mercurial class doesn't support
    # updating to a different branch than the one specified by
    # the user (like "default").  This is nonsense if we need
    # an auxiliary check-out :-(  At least I didn't find how.
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
    # here, update without caring about branches
    factory.addStep(ShellCmd(description="hg update",
           command=WithProperties("hg update --clean %(revision)s"),
           workdir=workdir))

def update_hg(platform, factory, repourl, workdir, use_branch,
              force_branch=None):
    if not use_branch:
        assert force_branch is None
        update_hg_old_method(platform, factory, repourl, workdir)
        return
    factory.addStep(
            Mercurial(
                repourl=repourl,
                mode='full',
                method='fresh',
                defaultBranch=force_branch,
                branchType='inrepo',
                clobberOnBranchChange=False,
                workdir=workdir,
                logEnviron=False))

def update_git(platform, factory, repourl, workdir, branch='master',
               alwaysUseLatest=False):
    factory.addStep(
            Git(
                repourl=repourl,
                mode='full',
                method='fresh',
                workdir=workdir,
                branch=branch,
                alwaysUseLatest=alwaysUseLatest,
                logEnviron=False))

def setup_steps(platform, factory, workdir=None,
                repourl='https://bitbucket.org/pypy/pypy/',
                force_branch=None):
    # XXX: this assumes that 'hg' is in the path
    import getpass
    if getpass.getuser() == 'antocuni':
        # for debugging
        repourl = '/home/antocuni/pypy/default'
    #
    factory.addStep(ParseRevision(hideStepIf=ParseRevision.hideStepIf,
                                  doStepIf=ParseRevision.doStepIf))
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
    factory.addStep(shell.SetPropertyFromCommand(
            command=['python', '-c', "import tempfile, os ;print"
                     " tempfile.gettempdir() + os.path.sep"],
             property="target_tmpdir"))
    # If target_tmpdir is empty, crash.
    tmp_or_crazy = '%(prop:target_tmpdir:-crazy/name/so/mkdir/fails/)s'
    pytest = "pytest"
    factory.addStep(ShellCmd( 
        description="mkdir for tests",
        command=['python', '-c', Interpolate("import os;  os.mkdir(r'" + \
                    tmp_or_crazy + pytest + "') if not os.path.exists(r'" + \
                    tmp_or_crazy + pytest + "') else True")],
        haltOnFailure=True,
        ))

    nDays = '3' #str, not int
    if platform == 'win32':
        command = ['FORFILES', '/P', Interpolate(tmp_or_crazy + pytest),
                   '/D', '-' + nDays, '/c', "cmd /c rmdir /q /s @path"]
    else:
        command = ['find', Interpolate(tmp_or_crazy + pytest), '-mtime',
                   '+' + nDays, '-exec', 'rm', '-r', '{}', ';'] 
    factory.addStep(SuccessAlways(
        description="cleanout old test files",
        command = command,
        flunkOnFailure=False,
        haltOnFailure=False,
        ))

    if app_tests:
        if app_tests == True:
            app_tests = []
        factory.addStep(PytestCmd(
            description="app-level (-A) test",
            command=prefix + ["python", "testrunner/runner.py",
                     "--logfile=pytest-A.log",
                     "--config=pypy/pytest-A.cfg",
                     "--config=pypy/pytest-A.py",
                     "--config=~/machine-A_cfg.py",
                     "--root=pypy", "--timeout=3600"
                     ] + ["--config=%s" % cfg for cfg in app_tests],
            logfiles={'pytestLog': 'pytest-A.log'},
            timeout=4000,
            env={"PYTHONPATH": ['.'],
                 "TMPDIR": Interpolate('%(prop:target_tmpdir)s' + pytest),
                }))

    if lib_python:
        factory.addStep(PytestCmd(
            description="lib-python test",
            command=prefix + ["python", "pypy/test_all.py",
                     "--pypy=pypy/goal/pypy-c",
                     "--timeout=3600",
                     "--resultlog=cpython.log", "lib-python"],
            timeout=4000,
            logfiles={'pytestLog': 'cpython.log'},
            env={"TMPDIR": Interpolate('%(prop:target_tmpdir)s' + pytest),
                }))

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
            logfiles={'pytestLog': 'pypyjit.log'},
            env={"TMPDIR": Interpolate('%(prop:target_tmpdir)s' + pytest),
                }))
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
            logfiles={'pytestLog': 'pypyjit_new.log'},
            env={"TMPDIR": Interpolate('%(prop:target_tmpdir)s' + pytest),
                }))


# ----

class Own(factory.BuildFactory):

    def __init__(self, platform='linux', cherrypick='', extra_cfgs=[], **kwargs):
        factory.BuildFactory.__init__(self)

        setup_steps(platform, self)

        timeout=kwargs.get('timeout', 4000)

        self.addStep(shell.SetPropertyFromCommand(
                command=['python', '-c', "import tempfile, os ;print"
                         " tempfile.gettempdir() + os.path.sep"],
                 property="target_tmpdir"))
        # If target_tmpdir is empty, crash.
        tmp_or_crazy = '%(prop:target_tmpdir:-crazy/name/so/mkdir/fails/)s'
        pytest = "pytest"
        self.addStep(ShellCmd( 
            description="mkdir for tests",
            command=['python', '-c', Interpolate("import os;  os.mkdir(r'" + \
                        tmp_or_crazy + pytest + "') if not os.path.exists(r'" + \
                        tmp_or_crazy + pytest + "') else True")],
            haltOnFailure=True,
            ))

        nDays = '3' #str, not int
        if platform == 'win32':
            command = ['FORFILES', '/P', Interpolate(tmp_or_crazy + pytest),
                       '/D', '-' + nDays, '/c', "cmd /c rmdir /q /s @path"]
        else:
            command = ['find', Interpolate(tmp_or_crazy + pytest), '-mtime',
                       '+' + nDays, '-exec', 'rm', '-r', '{}', ';'] 
        self.addStep(SuccessAlways(
            description="cleanout old test files",
            command = command,
            flunkOnFailure=False,
            haltOnFailure=False,
            ))

        self.addStep(ShellCmd(
            description="create virtualenv for tests",
            command=['virtualenv', 'virt_test'],
            haltOnFailure=True,
            ))

        if platform == 'win32':
            virt_python = r'virt_test\Scripts\python.exe'
        else:
            virt_python = 'virt_test/bin/python'

        self.addStep(ShellCmd(
            description="install requirments to virtual environment",
            command=[virt_python, '-mpip', 'install', '-r', 'requirements.txt'],
            haltOnFailure=True,
            ))

        self.addStep(PytestCmd(
            description="pytest pypy",
            command=[virt_python, "testrunner/runner.py",
                     "--logfile=testrun.log",
                     "--config=pypy/testrunner_cfg.py",
                     "--config=~/machine_cfg.py",
                     "--root=pypy", "--timeout=%s" % (timeout,)
                     ] + ["--config=%s" % cfg for cfg in extra_cfgs],
            logfiles={'pytestLog': 'testrun.log'},
            timeout=timeout,
            env={"PYTHONPATH": ['.'],
                 "PYPYCHERRYPICK": cherrypick,
                 "TMPDIR": Interpolate('%(prop:target_tmpdir)s' + pytest),
                 }))

        self.addStep(PytestCmd(
            description="pytest rpython",
            command=[virt_python, "testrunner/runner.py",
                     "--logfile=testrun.log",
                     "--config=pypy/testrunner_cfg.py",
                     "--config=~/machine_cfg.py",
                     "--root=rpython", "--timeout=%s" % (timeout,)
                     ] + ["--config=%s" % cfg for cfg in extra_cfgs],
            logfiles={'pytestLog': 'testrun.log'},
            timeout=timeout,
            env={"PYTHONPATH": ['.'],
                 "PYPYCHERRYPICK": cherrypick,
                 "TMPDIR": Interpolate('%(prop:target_tmpdir)s' + pytest),
                 }))


class Translated(factory.BuildFactory):

    def __init__(self, platform='linux',
                 translationArgs=['-O2'], targetArgs=[],
                 app_tests=False,
                 interpreter='pypy',
                 lib_python=False,
                 pypyjit=False,
                 prefix=None,
                 trigger=None,
                 ):
        factory.BuildFactory.__init__(self)
        if prefix is not None:
            prefix = prefix.split()
        else:
            prefix = []

        setup_steps(platform, self)

        self.addStep(Translate(translationArgs, targetArgs,
                               interpreter=interpreter))

        name = build_name(platform, pypyjit, translationArgs)
        self.addStep(ShellCmd(
            description="compress pypy-c",
            haltOnFailure=False,
            command=prefix + ["python", "pypy/tool/release/package.py",
                              "--targetdir=.", ".", WithProperties(name)],
            workdir='build'))
        nightly = '~/nightly/'
        extension = get_extension(platform)
        pypy_c_rel = "build/" + name + extension
        self.addStep(PyPyUpload(slavesrc=WithProperties(pypy_c_rel),
                                masterdest=WithProperties(nightly),
                                basename=name + extension,
                                workdir='.',
                                blocksize=100 * 1024))

        if trigger: # if provided trigger schedulers that depend on this one
            self.addStep(Trigger(schedulerNames=[trigger]))

        add_translated_tests(self, prefix, platform, app_tests, lib_python, pypyjit)


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
        name = build_name(platform, pypyjit, translationArgs, placeholder='%(final_file_name)s') + extension
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
                workdir='pypy-c',
                haltOnFailure=True,
                ))

        self.addStep(ShellCmd(
            description="reset permissions",
            command=['chmod', 'u+rw', '-R', 'build/include'],
            haltOnFailure=True,
            workdir='.'))
        # copy pypy-c to the expected location within the pypy source checkout
        command = ('PYPY_C="pypy-c/bin/pypy";'
                   'if [ -e pypy-c/bin/pypy3 ]; then PYPY_C="pypy-c/bin/pypy3"; fi;'
                   'cp -v $PYPY_C build/pypy/goal/pypy-c;')
        self.addStep(ShellCmd(
            description="move pypy-c",
            command=command,
            haltOnFailure=True,
            workdir='.'))
        # copy libpypy-c.so to the expected location within the pypy source checkout, if available
        command = 'if [ -e pypy-c/bin/libpypy-c.so ]; then cp -v pypy-c/bin/libpypy-c.so build/pypy/goal/; fi;'
        self.addStep(ShellCmd(
            description="move libpypy-c.so",
            command=command,
            haltOnFailure=True,
            workdir='.'))
        # copy generated and copied header files to build/include
        self.addStep(ShellCmd(
            description="move header files",
            command=['cp', '-vr', 'pypy-c/include', 'build'],
            haltOnFailure=True,
            workdir='.'))
        # copy ctypes_resource_cache generated during translation
        self.addStep(ShellCmd(
            description="reset permissions",
            command=['chmod', 'u+rw', '-R', 'build/lib_pypy'],
            haltOnFailure=True,
            workdir='.'))
        self.addStep(ShellCmd(
            description="copy ctypes resource cache",
            command=['cp', '-rv', 'pypy-c/lib_pypy/ctypes_config_cache', 'build/lib_pypy'],
            haltOnFailure=True,
            workdir='.'))
        self.addStep(ShellCmd(
            description="copy cffi import libraries",
            command='cp -rv pypy-c/lib_pypy/*.so build/lib_pypy',
            haltOnFailure=True,
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
                              "--targetdir=.", ".", WithProperties(name)],
            haltOnFailure=True,
            workdir='build'))
        nightly = '~/nightly/'
        extension = get_extension(platform)
        pypy_c_rel = "build/" + name + extension
        self.addStep(PyPyUpload(slavesrc=WithProperties(pypy_c_rel),
                                masterdest=WithProperties(nightly),
                                basename=name + extension,
                                workdir='.',
                                blocksize=100 * 1024))
        if trigger: # if provided trigger schedulers that depend on this one
            self.addStep(Trigger(schedulerNames=[trigger]))

class JITBenchmarkSingleRun(factory.BuildFactory):
    def __init__(self, platform='linux', host='tannit', postfix=''):
        factory.BuildFactory.__init__(self)

        repourl = 'https://bitbucket.org/pypy/benchmarks'
        update_hg(platform, self, repourl, 'benchmarks', use_branch=True,
                  force_branch='single-run')
        #
        setup_steps(platform, self)
        if host == 'tannit':
            lock = TannitCPU
        elif host == 'speed_python':
            lock = SpeedPythonCPU
        else:
            assert False, 'unknown host %s' % host

        self.addStep(
            Translate(
                translationArgs=['-Ojit'],
                targetArgs=[],
                haltOnFailure=True,
                # this step can be executed in parallel with other builds
                locks=[lock.access('counting')],
                )
            )
        pypy_c_rel = "../build/pypy/goal/pypy-c"
        self.addStep(ShellCmd(
            # this step needs exclusive access to the CPU
            locks=[lock.access('exclusive')],
            description="run benchmarks on top of pypy-c",
            command=["python", "runner.py", '--output-filename', 'result.json',
                     '--python', pypy_c_rel,
                     '--revision', WithProperties('%(got_revision)s'),
                     '--branch', WithProperties('%(branch)s'),
                     '--force-interpreter-name', 'pypy-c-jit',
                     ],
            workdir='./benchmarks',
            timeout=3600))
        # a bit obscure hack to get both os.path.expand and a property
        filename = '%(got_revision)s' + (postfix or '')
        resfile = os.path.expanduser("~/bench_results_new/%s.json" % filename)
        self.addStep(transfer.FileUpload(slavesrc="benchmarks/result.json",
                                         masterdest=WithProperties(resfile),
                                         workdir="."))

class JITBenchmark(factory.BuildFactory):
    def __init__(self, platform='linux', host='tannit', postfix=''):
        factory.BuildFactory.__init__(self)

        #
        repourl = 'https://bitbucket.org/pypy/benchmarks'
        update_hg(platform, self, repourl, 'benchmarks', use_branch=False)
        #
        setup_steps(platform, self)
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
        pypy_c_rel = "../build/pypy/goal/pypy-c"
        self.addStep(ShellCmd(
            # this step needs exclusive access to the CPU
            locks=[lock.access('exclusive')],
            description="run benchmarks on top of pypy-c",
            command=["python", "runner.py", '--output-filename', 'result.json',
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

        # check out and update benchmarks
        repourl = 'https://bitbucket.org/pypy/benchmarks'
        update_hg(platform, self, repourl, 'benchmarks', use_branch=False)

        # checks out and updates the repo
        setup_steps(platform, self, repourl='http://hg.python.org/cpython',
                    force_branch=branch)

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

class PyPyBuildbotTestFactory(factory.BuildFactory):
    def __init__(self):
        factory.BuildFactory.__init__(self)
        # clone
        self.addStep(
            Mercurial(
                repourl='https://bitbucket.org/pypy/buildbot',
                mode='incremental',
                method='fresh',
                defaultBranch='default',
                branchType='inrepo',
                clobberOnBranchChange=False,
                logEnviron=False))
        # create a virtualenv
        self.addStep(ShellCmd(
            description='create virtualenv',
            haltOnFailure=True,
            command='virtualenv --clear ../venv'))
        # install deps
        self.addStep(ShellCmd(
            description="install dependencies",
            haltOnFailure=True,
            command=('../venv/bin/pip install -r requirements.txt').split()))
        # run tests
        self.addStep(PytestCmd(
            description="pytest buildbot",
            haltOnFailure=True,
            command=["../venv/bin/py.test",
                     "--resultlog=testrun.log",
                     ],
            logfiles={'pytestLog': 'testrun.log'}))


class NativeNumpyTests(factory.BuildFactory):
    '''
    Download a pypy nightly, install nose and numpy, and run the numpy test suite
    '''
    def __init__(self, platform='linux',
                 app_tests=False,
                 lib_python=False,
                 pypyjit=True,
                 prefix=None,
                 translationArgs=[]
                 ):
        factory.BuildFactory.__init__(self)

        self.addStep(ParseRevision(hideStepIf=ParseRevision.hideStepIf,
                                  doStepIf=ParseRevision.doStepIf))
        # download corresponding nightly build
        if platform == 'win32':
            target = r'pypy-c\pypy.exe'
            untar = ['unzip']
            sep = '\\'
        else:
            target = r'pypy-c/bin/pypy'
            untar = ['tar', '--strip-components=1', '--directory=.', '-xf']
            sep = '/'
        self.addStep(ShellCmd(
            description="Clear",
            # assume, as part of git, that windows has rm
            command=['rm', '-rf', 'pypy-c', 'install'],
            workdir='.'))
        extension = get_extension(platform)
        name = build_name(platform, pypyjit, translationArgs, placeholder='%(final_file_name)s') + extension
        self.addStep(PyPyDownload(
            basename=name,
            mastersrc='~/nightly',
            slavedest='pypy_build' + extension,
            workdir='pypy-c'))

        # extract downloaded file
        self.addStep(ShellCmd(
            description="decompress pypy-c",
            command=untar + ['pypy_build'+ extension],
            workdir='pypy-c',
            haltOnFailure=True,
            ))
        
        if platform == 'win32':
            self.addStep(ShellCmd(
                description='move decompressed dir',
                command = ['mv', '*/*', '.'],
                workdir='pypy-c',
                haltOnFailure=True,
                ))

        # virtualenv the download
        self.addStep(ShellCmd(
            description="create virtualenv",
            command=['virtualenv','-p', target, 'install'],
            workdir='./',
            haltOnFailure=True,
            ))

        self.addStep(ShellCmd(
            description="report version",
            command=[sep.join(['install','bin','pypy'])] + ['--version'],
            workdir='./',
            haltOnFailure=True,
            ))

        self.addStep(ShellCmd(
            description="install nose",
            command=[sep.join(['install','bin','pip'])] + ['install','nose'],
            workdir='./',
            haltOnFailure=True,
            ))

        # obtain a pypy-compatible branch of numpy
        numpy_url = 'https://www.bitbucket.org/pypy/numpy'
        update_git(platform, self, numpy_url, 'numpy_src', branch='master',
                   alwaysUseLatest=True, # ignore pypy rev number when 
                                         # triggered by a pypy build
                   )

        self.addStep(ShellCmd(
            description="install numpy",
            command=[sep.join(['..', 'install', 'bin', 'pypy'])] + ['setup.py','install'],
            workdir='numpy_src'))

        self.addStep(ShellCmd(
            description="test numpy",
            command=[sep.join(['..', 'install', 'bin', 'pypy'])] + ['runtests.py'],
            #logfiles={'pytestLog': 'pytest-numpy.log'},
            timeout=4000,
            workdir='numpy_src',
        ))
        if platform != 'win32':
            self.addStep(ShellCmd(
                description="install jinja2",
                command=['install/bin/pip', 'install', 'jinja2'],
                workdir='./',
                haltOnFailure=True,))
            pypy_c_rel = 'install/bin/python'
            self.addStep(ShellCmd(
                description="measure numpy compatibility",
                command=[pypy_c_rel,
                         'numpy_src/tools/numready/',
                         pypy_c_rel, 'numpy-compat.html'],
                workdir="."))
            resfile = os.path.expanduser("~/numpy_compat/%(got_revision)s.html")
            self.addStep(NumpyStatusUpload(
                slavesrc="numpy-compat.html",
                masterdest=WithProperties(resfile),
                workdir="."))
