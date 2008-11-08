from buildbot.process import factory
from buildbot.steps import source, shell
from buildbot.status.builder import SUCCESS
import os

class ShellCmd(shell.ShellCommand):
    # our own version that can distinguish abort cases (rc == -1)

    def getText(self, cmd, results):
        if cmd is not None and cmd.rc == -1:
            return self.describe(True) + ['aborted']
        return shell.ShellCommand.getText(self, cmd, results)
    

class FirstTime(shell.SetProperty):

    def __init__(self, **kwds):
        shell.SetProperty.__init__(self, description="first-time",
                                   property="first-time")


class PosixFirstTime(FirstTime):
    command = "test -d pypy || echo yes"

class WindowsFirstTime(FirstTime):
    command = "if not exist pypy echo yes"    


class CondShellCommand(ShellCmd):

    def __init__(self, **kwds):
        ShellCmd.__init__(self, **kwds)
        self.cond = kwds.get('cond', lambda props: True)

    def start(self):
        props = self.build.getProperties()
        yes = self.cond(props)
        if yes:
            ShellCmd.start(self)
        else:
            self.setStatus(None, SUCCESS)
            self.finished(SUCCESS)

class Translate(ShellCmd):
    name = "translate"
    description = ["translating"]
    descriptionDone = ["translation"]

    command = ["python", "translate.py", "--batch"]
    translationTarget = "targetpypystandalone"
    haltOnFailure = True

    def __init__(self, translationArgs, targetArgs,
                 workdir="build/pypy/translator/goal",
                 *a, **kw):
        kw['translationArgs'] = translationArgs
        kw['targetArgs'] = targetArgs
        kw['timeout'] = 3600
        ShellCmd.__init__(self, workdir, *a, **kw)
        self.command = (self.command + translationArgs +
                        [self.translationTarget] + targetArgs)


# ________________________________________________________________

def not_first_time(props):
    first_time = props.getProperty("first-time")
    return not first_time 

def setup_steps(platform, factory, workdir=None):
    if platform == "win32":
        first_time_check = WindowsFirstTime()
    else:
        first_time_check = PosixFirstTime()

    factory.addStep(first_time_check)
    factory.addStep(CondShellCommand(
        description="wcrevert",
        cond=not_first_time,
        command = ["python", "py/bin/py.svnwcrevert", 
                   "-p.buildbot-sourcedata", "."],
        workdir = workdir,
        ))
    factory.addStep(source.SVN(baseURL="http://codespeak.net/svn/pypy/",
                               defaultBranch="trunk",
                               workdir=workdir))


class PyPyOwnTestFactory(factory.BuildFactory):

    def __init__(self, *a, **kw):
        platform = kw.pop('platform', 'linux')
        factory.BuildFactory.__init__(self, *a, **kw)

        setup_steps(platform, self)

        self.addStep(ShellCmd(
            description="pytest",
            command=["python", "testrunner/runner.py",
                     "--logfile=testrun.log",
                     "--config=pypy/testrunner_cfg.py",
                     "--config=~/machine_cfg.py",
                     "--root=pypy", "--timeout=3600"],
            logfiles={'pytestLog': 'testrun.log'},
            timeout = 4000,
            env={"PYTHONPATH": ['.']}))

class PyPyTranslatedLibPythonTestFactory(factory.BuildFactory):

    def __init__(self, *a, **kw):
        platform = kw.pop('platform', 'linux')
        factory.BuildFactory.__init__(self, *a, **kw)

        setup_steps(platform, self)

        self.addStep(Translate(["-O2"], []))

        self.addStep(ShellCmd(
            description="lib-python test",
            command=["python", "pypy/test_all.py",
                     "--pypy=pypy/translator/goal/pypy-c",
                     "--resultlog=cpython.log", "lib-python"],           
            logfiles={'pytestLog': 'cpython.log'}))

class PyPyTranslatedAppLevelTestFactory(factory.BuildFactory):

    def __init__(self, *a, **kw):
        platform = kw.pop('platform', 'linux')
        factory.BuildFactory.__init__(self, *a, **kw)

        setup_steps(platform, self)

        self.addStep(Translate(["-O2"], []))

        self.addStep(ShellCmd(
            description="app-level (-A) test",
            command=["python", "testrunner/runner.py",
                     "--logfile=pytest-A.log",
                     "--config=pypy/pytest-A.cfg",
                     "--root=pypy", "--timeout=1800"],
            logfiles={'pytestLog': 'pytest-A.log'},
            timeout = 4000,
            env={"PYTHONPATH": ['.']}))

class PyPyTranslatedScratchboxTestFactory(factory.BuildFactory):
    def __init__(self, *a, **kw):
        USERNAME = 'buildbot'
        WORKDIR = '/scratchbox/users/%s/home/%s/' % (USERNAME, USERNAME)
        
        factory.BuildFactory.__init__(self, *a, **kw)
        platform = kw.pop('platform', 'linux')
        setup_steps(platform, self, WORKDIR)
        workdir = os.path.join(WORKDIR, 'pypy', 'translator', 'goal')

        #self.addStep(Translate(["--platform", "maemo", "-Omem"], [],
        #                       workdir=workdir))
        
        self.addStep(ShellCmd(
            description="app-level (-A) test",
            command=["python", "testrunner/runner.py",
                     "--dry-run",
                     "--logfile=pytest-A.log",
                     "--config=pypy/pytest-scratchbox-A.cfg",
                     "--root=pypy", "--timeout=1800"],
            logfiles={'pytestLog': 'pytest-A.log'},
            timeout = 4000,
            env={"PYTHONPATH": ['.']}))
