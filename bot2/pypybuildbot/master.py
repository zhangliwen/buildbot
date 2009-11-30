from buildbot.scheduler import Nightly
from buildbot.buildslave import BuildSlave
from buildbot.status.html import WebStatus


# I really wanted to pass logPath to Site
from twisted.web.server import Site
class LoggingSite(Site):
    def __init__(self, *a, **kw):
        Site.__init__(self, logPath='httpd.log', *a, **kw)
from twisted.web import server
if server.Site.__name__ == 'Site':
    server.Site = LoggingSite
# So I did.


# The button Resubmit Build is quite confusing, so disable it
from buildbot.status.web.build import StatusResourceBuild
StatusResourceBuild_init = StatusResourceBuild.__init__
def my_init(self, build_status, build_control, builder_control):
    StatusResourceBuild_init(self, build_status, build_control, None)
StatusResourceBuild.__init__ = my_init
# Disabled.

# Disable pinging, as it seems to deadlock the client
from buildbot.status.web.builder import StatusResourceBuilder
def my_ping(self, req):
    raise Exception("pinging is disabled, as it seems to deadlock clients")
StatusResourceBuilder.ping = my_ping
# Disabled.


status = WebStatus(httpPortNumber, allowForce=True)

# pypy test summary page
summary = load('pypybuildbot.summary')
status.putChild('summary', summary.Summary(['own', 'applevel',
                                            'lib-python', 'jit',
                                            'stackless',
                                            'windows', 'mac',
                                            'benchmark-run',
                                            'maemo', 'other']))


pypybuilds = load('pypybuildbot.builds')

pypyOwnTestFactory = pypybuilds.Own()
pypyOwnTestFactoryWin = pypybuilds.Own(platform="win32")
pypyJitOnlyOwnTestFactory = pypybuilds.Own(cherrypick="jit")

pypyTranslatedAppLevelTestFactory = pypybuilds.Translated(lib_python=True,
                                                          app_tests=True)

pypyStacklessTranslatedAppLevelTestFactory = pypybuilds.Translated(
    translationArgs=["-O2", "--stackless"], targetArgs=[],
    lib_python=False,
    app_tests = ["pypy/pytest-A-stackless.cfg"]
)

pypyTranslatedAppLevelTestFactoryWin = pypybuilds.Translated(
    platform="win32",
    lib_python=True,
    app_tests=True)

pypyJITTranslatedTestFactory = pypybuilds.Translated(
    translationArgs=['-Ojit', '--gc=hybrid',
                     '--gcrootfinder=asmgcc',
                     '--jit-debug=steps'],
    targetArgs = ['--withoutmod-thread'],
    lib_python=True,
    pypyjit=True
    )

pypy_OjitTranslatedTestFactory = pypybuilds.Translated(
    translationArgs=['-Ojit', '--gc=hybrid', '--no-translation-jit'
                     '--gcrootfinder=asmgcc'],
    lib_python=True,
    app_tests=True
    )

pypyJITBenchmarkFactory = pypybuilds.JITBenchmark()

pypyTranslatedLibPythonMaemoTestFactory = pypybuilds.TranslatedScratchbox()


LINUX32 = "own-linux-x86-32"
MACOSX32 =  "own-macosx-x86-32"
APPLVLLINUX32 = "pypy-c-app-level-linux-x86-32"
STACKLESSAPPLVLLINUX32 = "pypy-c-stackless-app-level-linux-x86-32"

APPLVLWIN32 = "pypy-c-app-level-win-32"
APPLVLFREEBSD64 = 'pypy-c-app-level-freebsd-7-x86-64'

JITLINUX32 = "pypy-c-jit-linux-x86-32"
OJITLINUX32 = "pypy-c-Ojit-no-jit-linux-x86-32"

JITONLYLINUX32 = "jitonly-own-linux-x86-32"
JITBENCH = "jit-benchmark-linux-x86-32"

BUILDMAEMO = "pypy-c-maemo-build"

BuildmasterConfig = {
    'slavePortnum': slavePortnum,

    'change_source': [],
    'schedulers': [
    	Nightly("nightly", [LINUX32, APPLVLLINUX32, APPLVLWIN32,
                            STACKLESSAPPLVLLINUX32, JITLINUX32, OJITLINUX32,
                            MACOSX32],
                hour=4, minute=45),
        Nightly("nightly-benchmark", [JITBENCH],
                hour=2, minute=25),
    ],
    'status': [status],

    'slaves': [BuildSlave(name, password)
               for (name, password)
               in passwords.iteritems()],

    'builders': [
                  {"name": LINUX32,
                   "slavenames": ["wyvern"],
                   "builddir": LINUX32,
                   "factory": pypyOwnTestFactory,
                   "category": 'own'
                  },
                  {"name": MACOSX32,
                   "slavenames": ["minime"],
                   "builddir": MACOSX32,
                   "factory": pypyOwnTestFactory,
                   "category": 'mac'
                  },                  
                  {"name": APPLVLLINUX32,
                   "slavenames": ["wyvern", "cobra"],
                   "builddir": APPLVLLINUX32,
                   "factory": pypyTranslatedAppLevelTestFactory,
                   'category': 'applevel'
                  },
                  {"name": STACKLESSAPPLVLLINUX32,
                   "slavenames": ["wyvern", "cobra"],
                   "builddir": STACKLESSAPPLVLLINUX32,
                   "factory": pypyStacklessTranslatedAppLevelTestFactory,
                   "category": 'stackless'
                  },
                  {"name": OJITLINUX32,
                   "slavenames": ["wyvern", "cobra"],
                   "builddir": OJITLINUX32,
                   "factory": pypy_OjitTranslatedTestFactory,
                   "category": 'applevel'
                  },                   
                  {"name": APPLVLWIN32,
                   "slavenames": ["bigboard"],
                   "builddir": APPLVLWIN32,
                   "factory": pypyTranslatedAppLevelTestFactoryWin,
                   "category": "windows"
                  },
                  {"name" : BUILDMAEMO,
                   "slavenames": ['bigdogvm1'],
                   "builddir" : BUILDMAEMO,
                   "factory": pypyTranslatedLibPythonMaemoTestFactory,
                   "category": 'maemo'
                   },
                  {"name" : APPLVLFREEBSD64,
                   "slavenames": ['headless'],
                   'builddir' : APPLVLFREEBSD64,
                   'factory' : pypyTranslatedAppLevelTestFactory,
                   "category": 'other'
                   },
                  {"name" : JITLINUX32,
                   "slavenames": ["bigdogvm1"],
                   'builddir' : JITLINUX32,
                   'factory' : pypyJITTranslatedTestFactory,
                   'category' : 'jit',
                   },
                  {"name": JITONLYLINUX32,
                   "slavenames": ["wyvern"],
                   "builddir": JITONLYLINUX32,
                   "factory": pypyJitOnlyOwnTestFactory,
                   "category": 'own'
                  },
                  {"name": JITBENCH,
                   "slavenames": ["bigdogvm2"],
                   "builddir": JITBENCH,
                   "factory": pypyJITBenchmarkFactory,
                   "category": 'benchmark-run',
                  },
                ],

    'buildbotURL': 'http://codespeak.net:%d/'%(httpPortNumber),
    'projectURL': 'http://codespeak.net/pypy/',
    'projectName': 'PyPy'}

CACHESIZE = 80 # cache size for build outcomes

estimated = (sum([len(_sched.listBuilderNames())
             for _sched in BuildmasterConfig['schedulers']]) * 6)

if estimated > CACHESIZE:
    raise ValueError("master.py CACHESIZE (%d) is too small considered"
                     " a builder*scheduler combinations based estimate (%d)"
                     % (CACHESIZE, estimated))
summary.outcome_set_cache.cachesize = CACHESIZE
