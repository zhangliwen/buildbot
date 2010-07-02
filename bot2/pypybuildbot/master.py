from buildbot.scheduler import Nightly
from buildbot.buildslave import BuildSlave
from buildbot.status.html import WebStatus
from buildbot.process.builder import Builder
from pypybuildbot.pypylist import PyPyList

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

# Picking a random slave is not really what we want;
# let's pick the first available one instead.
Builder.CHOOSE_SLAVES_RANDOMLY = False


status = WebStatus(httpPortNumber, allowForce=True)

# pypy test summary page
summary = load('pypybuildbot.summary')
status.putChild('summary', summary.Summary(['own', 'applevel',
                                            'lib-python', 'jit',
                                            'stackless',
                                            'windows', 'mac',
                                            'benchmark-run',
                                            'other']))
status.putChild('nightly', PyPyList(os.path.expanduser('~/nightly'),
                                    defaultType='application/octet-stream'))


pypybuilds = load('pypybuildbot.builds')

pypyOwnTestFactory = pypybuilds.Own()
pypyOwnTestFactoryWin = pypybuilds.Own(platform="win32")
pypyJitOnlyOwnTestFactory = pypybuilds.Own(cherrypick="jit")

pypyTranslatedAppLevelTestFactory = pypybuilds.Translated(lib_python=True,
                                                          app_tests=True)
pypyTranslatedAppLevelTestFactory64 = pypybuilds.Translated(lib_python=True,
                                                            app_tests=True,
                                                            platform='linux64')

pypyStacklessTranslatedAppLevelTestFactory = pypybuilds.Translated(
    translationArgs=["-O2", "--stackless"], targetArgs=[],
    lib_python=False,
    app_tests = ["pypy/pytest-A-stackless.cfg"]
)

pypyTranslatedAppLevelTestFactoryWin = pypybuilds.Translated(
    platform="win32",
    lib_python=True,
    app_tests=True)

jit_translation_args = ['-Ojit', '--gc=hybrid',
                        '--gcrootfinder=asmgcc']

pypyJITTranslatedTestFactory = pypybuilds.Translated(
    translationArgs=jit_translation_args,
    targetArgs=[],
    lib_python=True,
    pypyjit=True,
    app_tests=True,
    )

pypyJITTranslatedTestFactoryOSX = pypybuilds.Translated(
    platform='osx',
    translationArgs=jit_translation_args,
    targetArgs=[],
    lib_python=True,
    pypyjit=True,
    app_tests=True,
    )

pypyJITTranslatedTestFactoryWin = pypybuilds.Translated(
    platform="win32",
    translationArgs=jit_translation_args,
    targetArgs=[],
    lib_python=True,
    pypyjit=True,
    app_tests=True,
    )

pypy_OjitTranslatedTestFactory = pypybuilds.Translated(
    translationArgs=['-Ojit', '--gc=hybrid', '--no-translation-jit',
                     '--gcrootfinder=asmgcc'],
    lib_python=True,
    app_tests=True
    )

pypyJITBenchmarkFactory = pypybuilds.JITBenchmark()

LINUX32 = "own-linux-x86-32"
LINUX64 = "own-linux-x86-64"
MACOSX32 =  "own-macosx-x86-32"
APPLVLLINUX32 = "pypy-c-app-level-linux-x86-32"
APPLVLLINUX64 = "pypy-c-app-level-linux-64"
STACKLESSAPPLVLLINUX32 = "pypy-c-stackless-app-level-linux-x86-32"

APPLVLWIN32 = "pypy-c-app-level-win-32"
STACKLESSAPPLVLFREEBSD64 = 'pypy-c-stackless-app-level-freebsd-7-x86-64'

JITLINUX32 = "pypy-c-jit-linux-x86-32"
OJITLINUX32 = "pypy-c-Ojit-no-jit-linux-x86-32"
JITMACOSX32 = "pypy-c-jit-macosx-x86-32"
JITWIN32 = "pypy-c-jit-win-x86-32"

JITONLYLINUX32 = "jitonly-own-linux-x86-32"
JITBENCH = "jit-benchmark-linux-x86-32"

BuildmasterConfig = {
    'slavePortnum': slavePortnum,

    'change_source': [],
    'schedulers': [
        Nightly("nightly-first", [LINUX32, LINUX64],
                hour=4, minute=44),
        Nightly("nightly", [APPLVLLINUX32, APPLVLLINUX64, APPLVLWIN32,
                            STACKLESSAPPLVLLINUX32, STACKLESSAPPLVLFREEBSD64,
                            JITLINUX32, OJITLINUX32,
                            MACOSX32],
                hour=4, minute=45),
        Nightly("nightly-benchmark", [JITBENCH],
                hour=6, minute=15),
    ],
    'status': [status],

    'slaves': [BuildSlave(name, password)
               for (name, password)
               in passwords.iteritems()],

    'builders': [
                  {"name": LINUX32,
                   "slavenames": ["cobra", "bigdogvm1", "tannit32"],
                   "builddir": LINUX32,
                   "factory": pypyOwnTestFactory,
                   "category": 'own'
                  },
		  {"name": LINUX64,
		   "slavenames": ["tannit64"],
		   "builddir": LINUX64,
		   "factory": pypyOwnTestFactory,
		   "category": 'own64'
		  },
                  {"name": MACOSX32,
                   "slavenames": ["minime"],
                   "builddir": MACOSX32,
                   "factory": pypyOwnTestFactory,
                   "category": 'mac'
                  },                  
                  {"name": APPLVLLINUX32,
                   "slavenames": ["bigdogvm1", "tannit32"],
                   "builddir": APPLVLLINUX32,
                   "factory": pypyTranslatedAppLevelTestFactory,
                   'category': 'applevel'
                  },
                  {"name": APPLVLLINUX64,
                   "slavenames": ["tannit64"],
                   "builddir": APPLVLLINUX64,
                   "factory": pypyTranslatedAppLevelTestFactory64,
                   "category": "applevel64"
                  },
                  {"name": STACKLESSAPPLVLLINUX32,
                   "slavenames": ["bigdogvm1", "tannit32"],
                   "builddir": STACKLESSAPPLVLLINUX32,
                   "factory": pypyStacklessTranslatedAppLevelTestFactory,
                   "category": 'stackless'
                  },
                  {"name": OJITLINUX32,
                   "slavenames": ["bigdogvm1", "tannit32"],
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
                  {"name" : STACKLESSAPPLVLFREEBSD64,
                   "slavenames": ['headless'],
                   'builddir' : STACKLESSAPPLVLFREEBSD64,
                   'factory' : pypyStacklessTranslatedAppLevelTestFactory,
                   "category": 'other'
                   },
                  {"name" : JITLINUX32,
                   "slavenames": ["bigdogvm1", "tannit32"],
                   'builddir' : JITLINUX32,
                   'factory' : pypyJITTranslatedTestFactory,
                   'category' : 'jit',
                   },
                  {"name" : JITMACOSX32,
                   "slavenames": ["minime"],
                   'builddir' : JITMACOSX32,
                   'factory' : pypyJITTranslatedTestFactoryOSX,
                   'category' : 'jit',
                   },
                  {"name" : JITWIN32,
                   "slavenames": ["bigboard"],
                   'builddir' : JITWIN32,
                   'factory' : pypyJITTranslatedTestFactoryWin,
                   'category' : 'jit',
                   },
                  {"name": JITONLYLINUX32,
                   "slavenames": ["tannit32", "bigdogvm1"],
                   "builddir": JITONLYLINUX32,
                   "factory": pypyJitOnlyOwnTestFactory,
                   "category": 'own'
                  },
                  {"name": JITBENCH,
                   "slavenames": ["tannit32"],
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
