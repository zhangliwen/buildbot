from buildbot.process import factory
from buildbot.steps import source, shell
from buildbot.status.builder import SUCCESS


class FirstTime(shell.SetProperty):

    def __init__(self, **kwds):
        shell.SetProperty.__init__(self, description="first-time",
                                   property="first-time")


class PosixFirstTime(FirstTime):
    command = "test -d pypy || echo yes"

class WindowsFirstTime(FirstTime):
    command = "if not exist pypy echo yes"    


class CondShellCommand(shell.ShellCommand):

    def __init__(self, **kwds):
        shell.ShellCommand.__init__(self, **kwds)
        self.cond = kwds.get('cond', lambda props: True)

    def start(self):
        props = self.build.getProperties()
        yes = self.cond(props)
        if yes:
            shell.ShellCommand.start(self)
        else:
            self.setStatus(None, SUCCESS)
            self.finished(SUCCESS)

class Translate(shell.ShellCommand):
    name = "translate"
    description = ["translating"]
    descriptionDone = ["translation"]

    command = ["echo", "python", "translate.py", "--batch"]
    translationTarget = "targetpypystandalone"

    def __init__(self, translationArgs, targetArgs,
                 workdir="build/pypy/translator/goal",
                 *a, **kw):
        kw['translationArgs'] = translationArgs
        kw['targetArgs'] = targetArgs
        shell.ShellCommand.__init__(self, workdir, *a, **kw)
        self.command = (self.command + translationArgs +
                        [self.translationTarget] + targetArgs)


# ________________________________________________________________

def not_first_time(props):
    first_time = props.getProperty("first-time")
    return not first_time 

def setup_steps(platform, factory):
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
        ))
    factory.addStep(source.SVN(baseURL="http://codespeak.net/svn/pypy/",
                            defaultBranch="dist"))    


class PyPyOwnTestFactory(factory.BuildFactory):

    def __init__(self, *a, **kw):
        platform = kw.pop('platform', 'linux')
        factory.BuildFactory.__init__(self, *a, **kw)

        setup_steps(platform, self)

        self.addStep(shell.ShellCommand(
            description="pytest",
            command=["python", "testrunner/runner.py",
                     "--logfile=testrun.log",
                     "--config=pypy/testrunner_cfg.py",
                     "--config=~/machine_cfg.py",
                     "--root=pypy"],
            logfiles={'pytestLog': 'testrun.log'},
            env={"PYTHONPATH": ['.']}))

class PyPyTranslaledLibPythonTestFactory(factory.BuildFactory):

    def __init__(self, *a, **kw):
        platform = kw.pop('platform', 'linux')
        factory.BuildFactory.__init__(self, *a, **kw)

        setup_steps(platform, self)

        self.addStep(Translate(["-O0"], ["-no-allworkingmodules"]))

        self.addStep(shell.ShellCommand(
            description="lib-python test",
            command=["python", "pypy/test_all.py",
                     "--pypy=pypy/translator/goal/pypy-c",
                     "--resultlog=cpython.log"],           
            logfiles={'pytestLog': 'cpython.log'}))
