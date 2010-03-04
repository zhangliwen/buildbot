from buildbot.process import factory
from buildbot.steps import source, shell, transfer
from buildbot.status.builder import SUCCESS
from buildbot.process.properties import WithProperties
import os

class ShellCmd(shell.ShellCommand):
    # our own version that can distinguish abort cases (rc == -1)

    def getText(self, cmd, results):
        if cmd is not None and cmd.rc == -1:
            return self.describe(True) + ['aborted']
        return shell.ShellCommand.getText(self, cmd, results)


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
        add_args = {'translationArgs': translationArgs,
                    'targetArgs': targetArgs}
        kw['timeout'] = 3600
        ShellCmd.__init__(self, workdir, *a, **kw)
        self.addFactoryArguments(**add_args)
        self.command = (self.command + translationArgs +
                        [self.translationTarget] + targetArgs)
        #self.command = ['cp', '/tmp/pypy-c', '.']

# ________________________________________________________________

def setup_steps(platform, factory, workdir=None):
    if platform == "win32":
        command = "if exist pypy %s"
    else:
        command = "if [ -d pypy ]; then %s; fi"
    command = command % "python py/bin/py.svnwcrevert -p.buildbot-sourcedata ."
    factory.addStep(ShellCmd(
        description="wcrevert",
        command = command,
        workdir = workdir,
        ))
    factory.addStep(source.SVN(baseURL="http://codespeak.net/svn/pypy/",
                               defaultBranch="trunk",
                               workdir=workdir))


class Own(factory.BuildFactory):

    def __init__(self, platform='linux', cherrypick='', extra_cfgs=[]):
        factory.BuildFactory.__init__(self)

        setup_steps(platform, self)

        self.addStep(ShellCmd(
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
            self.addStep(ShellCmd(
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
            self.addStep(ShellCmd(
                description="lib-python test",
                command=["python", "pypy/test_all.py",
                         "--pypy=pypy/translator/goal/pypy-c",
                         "--resultlog=cpython.log", "lib-python"],           
                logfiles={'pytestLog': 'cpython.log'}))

        if pypyjit:
            self.addStep(ShellCmd(
                description="pypyjit tests",
                command=["python", "pypy/test_all.py",
                         "--pypy=pypy/translator/goal/pypy-c",
                         "--resultlog=pypyjit.log",
                         "pypy/module/pypyjit/test"],
                logfiles={'pytestLog': 'pypyjit.log'}))            


class JITBenchmark(factory.BuildFactory):
    def __init__(self, platform='linux'):
        factory.BuildFactory.__init__(self)

        setup_steps(platform, self)
        self.addStep(ShellCmd(description="checkout benchmarks",
            command=['svn', 'co', 'http://codespeak.net/svn/pypy/benchmarks',
                     'benchmarks'],
            workdir='.'))
        self.addStep(Translate(['-Ojit'], []))
        self.addStep(ShellCmd(
            description="run more benchmarks on top of pypy-c-jit",
            command=["python", "runner.py", '--output-filename', 'result.json',
                    '--pypy-c', '../build/pypy/translator/goal/pypy-c',
                     '--upload', '--force-host', 'bigdog',
                     '--revision', WithProperties('%(got_revision)s')],
            workdir='./benchmarks',
            haltOnFailure=True))
        # a bit obscure hack to get both os.path.expand and a property
        resfile = os.path.expanduser("~/bench_results/%(got_revision)s.json")
        self.addStep(transfer.FileUpload(slavesrc="benchmarks/result.json",
                                         masterdest=WithProperties(resfile),
                                         workdir="."))
        self.addStep(ShellCmd(
            description="run more benchmarks on top of pypy-c no jit",
            command=["python", "runner.py", '--output-filename', 'result.json',
                    '--pypy-c', '../build/pypy/translator/goal/pypy-c',
                     '--revision', WithProperties('%(got_revision)s'),
                     '--upload', '--force-host', 'bigdog',
                     '--args', ',--jit threshold=1000000000'],
            workdir='./benchmarks',
            haltOnFailure=True))
        resfile = os.path.expanduser("~/bench_results_nojit/%(got_revision)s.json")
        self.addStep(transfer.FileUpload(slavesrc="benchmarks/result.json",
                                         masterdest=WithProperties(resfile),
                                         workdir="."))
        
        self.addStep(ShellCmd(
            description="run benchmarks 1",
            command=["python", "pypy/translator/benchmark/jitbench.py",
                     "pypy/translator/goal/pypy-c"]))

# xxx keep style
class TranslatedScratchbox(factory.BuildFactory):
    def __init__(self, *a, **kw):
        USERNAME = 'buildbot'
        WORKDIR = '/scratchbox/users/%s/home/%s/build' % (USERNAME, USERNAME)
        
        factory.BuildFactory.__init__(self, *a, **kw)
        platform = kw.pop('platform', 'linux')
        setup_steps(platform, self, WORKDIR)
        workdir = os.path.join(WORKDIR, 'pypy', 'translator', 'goal')

        self.addStep(Translate(["--platform", "maemo", "--gc=hybrid", "-Omem"],
                               [], workdir=workdir))
        
        #self.addStep(ShellCmd(
        #    description="app-level (-A) test",
        #    command=["python", "testrunner/scratchbox_runner.py",
        #             "--logfile=pytest-A.log",
        #             "--config=pypy/pytest-A.cfg",
        #             "--root=pypy", "--timeout=1800"],
        #    logfiles={'pytestLog': 'pytest-A.log'},
        #    timeout = 4000,
        #    workdir = WORKDIR,
        #    env={"PYTHONPATH": ['.']}))
        self.addStep(ShellCmd(
            description="copy build",
            command=["scp", "pypy-c", "fijal@codespeak.net:builds/pypy-c-scratchbox"], workdir = workdir))
