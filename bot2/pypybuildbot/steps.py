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

# ________________________________________________________________

def not_first_time(props):
    first_time = props.getProperty("first-time")
    return not first_time 

class PyPyOwnTestFactory(factory.BuildFactory):

    def __init__(self, *a, **kw):
        platform = kw.pop('platform', 'linux')
        factory.BuildFactory.__init__(self, *a, **kw)

        if platform == "win32":
            first_time_check = WindowsFirstTime()
        else:
            first_time_check = PosixFirstTime()

        self.addStep(first_time_check)
        self.addStep(CondShellCommand(
            description="wcrevert",
            cond=not_first_time,
            command = ["python", "py/bin/py.svnwcrevert", "."],
            haltOnFailure=True))
        self.addStep(source.SVN("https://codespeak.net/svn/pypy/"
                                "branch/pypy-pytrunk"))
        self.addStep(shell.ShellCommand(
            description="pytest",
            command=["python", "py/bin/py.test",
                     "pypy/module/__builtin__", "pypy/module/operator",
                     "--session=FileLogSession", "--filelog=pytest.log"],
            logfiles={'pytestLog': 'pytest.log'}))
