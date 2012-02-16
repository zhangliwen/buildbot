
import os
import getpass
from buildbot.scheduler import Nightly
from buildbot.buildslave import BuildSlave
from buildbot.status.html import WebStatus
from buildbot.process.builder import Builder
#from buildbot import manhole
from pypybuildbot.pypylist import PyPyList, NumpyStatusList
from pypybuildbot.ircbot import IRC # side effects

# Forbid "force build" with empty user name
from buildbot.status.web.builder import StatusResourceBuilder
def my_force(self, req, *args, **kwds):
    name = req.args.get("username", [""])[0]
    assert name, "Please write your name in the corresponding field."
    return _previous_force(self, req, *args, **kwds)
_previous_force = StatusResourceBuilder.force
if _previous_force.__name__ == 'force':
    StatusResourceBuilder.force = my_force
# Done

if getpass.getuser() == 'antocuni':
    channel = '#buildbot-test'
else:
    channel = '#pypy'

status = WebStatus(httpPortNumber, allowForce=True)
ircbot = IRC(host="irc.freenode.org",
             nick="bbot2",
             channels=[channel],
             notify_events={
                 'started': 1,
                 'finished': 1,
             })

# pypy test summary page
summary = load('pypybuildbot.summary')
status.putChild('summary', summary.Summary(categories=['linux',
                                                       'mac',
                                                       'win',
                                                       'freebsd']))
status.putChild('nightly', PyPyList(os.path.expanduser('~/nightly'),
                                    defaultType='application/octet-stream'))
status.putChild('numpy-status', NumpyStatusList(os.path.expanduser('~/numpy_compat')))


pypybuilds = load('pypybuildbot.builds')
TannitCPU = pypybuilds.TannitCPU

pypyOwnTestFactory = pypybuilds.Own()
pypyOwnTestFactoryWin = pypybuilds.Own(platform="win32")
pypyJitOnlyOwnTestFactory = pypybuilds.Own(cherrypick="jit")

pypyTranslatedAppLevelTestFactory = pypybuilds.Translated(lib_python=True,
                                                          app_tests=True)
pypyTranslatedAppLevelTestFactory64 = pypybuilds.Translated(lib_python=True,
                                                            app_tests=True,
                                                            platform='linux64')

pypyTranslatedAppLevelTestFactoryWin = pypybuilds.Translated(
    platform="win32",
    lib_python=True,
    app_tests=True,
    interpreter='python')

jit_translation_args = ['-Ojit']

pypyJITTranslatedTestFactory = pypybuilds.Translated(
    translationArgs=jit_translation_args,
    targetArgs=[],
    lib_python=True,
    pypyjit=True,
    app_tests=True,
    )
pypyJITTranslatedTestFactory64 = pypybuilds.Translated(
    translationArgs=jit_translation_args,
    targetArgs=[],
    lib_python=True,
    pypyjit=True,
    app_tests=True,
    platform='linux64',
    )

pypyJITTranslatedTestFactoryOSX = pypybuilds.Translated(
    platform='osx',
    translationArgs=jit_translation_args,
    targetArgs=[],
    lib_python=True,
    pypyjit=True,
    app_tests=True,
    interpreter='python',
    )

pypyJITTranslatedTestFactoryOSX64 = pypybuilds.Translated(
    platform='osx64',
    translationArgs=jit_translation_args,
    targetArgs=[],
    lib_python=True,
    pypyjit=True,
    app_tests=True,
    interpreter='python',
    )

pypyJITTranslatedTestFactoryWin = pypybuilds.Translated(
    platform="win32",
    translationArgs=jit_translation_args,
    targetArgs=[],
    lib_python=True,
    pypyjit=True,
    app_tests=True,
    interpreter='python',
    )

pypyJITTranslatedTestFactoryFreeBSD = pypybuilds.Translated(
    platform="freebsd64",
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

pypyJITBenchmarkFactory_tannit = pypybuilds.JITBenchmark()
pypyJITBenchmarkFactory64_tannit = pypybuilds.JITBenchmark(platform='linux64',
                                                           postfix='-64')
pypyJITBenchmarkFactory64_speed = pypybuilds.JITBenchmark(platform='linux64',
                                                          postfix='-64',
                                                          host='speed_python')

cPython27BenchmarkFactory64 = pypybuilds.CPythonBenchmark('2.7',
                                                          platform='linux64')


LINUX32 = "own-linux-x86-32"
LINUX64 = "own-linux-x86-64"
MACOSX32 =  "own-macosx-x86-32"
PPCLINUX32 =  "own-linux-ppc-32"
WIN32 = "own-win-x86-32"
WIN64 = "own-win-x86-64"
APPLVLLINUX32 = "pypy-c-app-level-linux-x86-32"
APPLVLLINUX64 = "pypy-c-app-level-linux-x86-64"

APPLVLWIN32 = "pypy-c-app-level-win-x86-32"

JITLINUX32 = "pypy-c-jit-linux-x86-32"
JITLINUX64 = "pypy-c-jit-linux-x86-64"
OJITLINUX32 = "pypy-c-Ojit-no-jit-linux-x86-32"
JITMACOSX64 = "pypy-c-jit-macosx-x86-64"
JITWIN32 = "pypy-c-jit-win-x86-32"
JITWIN64 = "pypy-c-jit-win-x86-64"
JITFREEBSD64 = 'pypy-c-jit-freebsd-7-x86-64'

JITONLYLINUX32 = "jitonly-own-linux-x86-32"
JITBENCH = "jit-benchmark-linux-x86-32"
JITBENCH64 = "jit-benchmark-linux-x86-64"
JITBENCH64_2 = 'jit-benchmark-linux-x86-64-2'
CPYTHON_64 = "cpython-2-benchmark-x86-64"


BuildmasterConfig = {
    'slavePortnum': slavePortnum,

    'change_source': [],
    ## 'schedulers': [
    ##     Nightly("nightly-0-00", [
    ##         JITBENCH,  # on tannit -- nothing else there during first round!
    ##         MACOSX32,                  # on minime
    ##         ], hour=0, minute=0),
    ##     Nightly("nighly-2-00", [
    ##         JITBENCH64, # on tannit -- nothing else there during first round!
    ##         ], hour=2, minute=0),
    ##     Nightly("nightly-4-00", [
    ##         # rule: what we pick here on tannit should take at most 8 cores
    ##         # and be hopefully finished after 2 hours
    ##         LINUX32,                   # on tannit32, uses 4 cores
    ##         JITLINUX32,                # on tannit32, uses 1 core
    ##         JITLINUX64,                # on tannit64, uses 1 core
    ##         OJITLINUX32,               # on tannit32, uses 1 core
    ##         JITWIN32,                  # on bigboard
    ##         STACKLESSAPPLVLFREEBSD64,  # on headless
    ##         JITMACOSX64,               # on mvt's machine
    ##         ], hour=4, minute=0),
    ##     Nightly("nightly-6-00", [
    ##         # there should be only JITLINUX32 that takes a bit longer than
    ##         # that.  We can use a few more cores now.
    ##         APPLVLLINUX32,           # on tannit32, uses 1 core
    ##         APPLVLLINUX64,           # on tannit64, uses 1 core
    ##         STACKLESSAPPLVLLINUX32,  # on tannit32, uses 1 core
    ##         ], hour=6, minute=0),
    ##     Nightly("nightly-7-00", [
    ##         # the remaining quickly-run stuff on tannit
    ##         LINUX64,                 # on tannit64, uses 4 cores
    ##         ], hour=7, minute=0),
    ## ],

    'schedulers': [
        # first of all, we run the benchmarks: the two translations take ~2800
        # seconds and are executed in parallel. Running benchmarks takes ~3400
        # seconds and is executed sequentially. In total, 2800 + (3300*2) ~=
        # 160 minutes
        Nightly("nightly-0-00", [
            JITBENCH,                  # on tannit32, uses 1 core (in part exclusively)
            JITBENCH64,                # on tannit64, uses 1 core (in part exclusively)
            JITBENCH64_2,              # on speed.python.org, uses 1 core (in part exclusively)
            CPYTHON_64,                # on speed.python.org, uses 1 core (in part exclusively)
            MACOSX32,                  # on minime
            ], branch=None, hour=0, minute=0),
        #
        # then, we schedule all the rest. The locks will take care not to run
        # all of them in parallel
        Nightly("nighly-3-00", [
            LINUX32,                   # on tannit32, uses 4 cores
            LINUX64,                   # on tannit64, uses 4 cores
            JITLINUX32,                # on tannit32, uses 1 core
            JITLINUX64,                # on tannit64, uses 1 core
            OJITLINUX32,               # on tannit32, uses 1 core
            APPLVLLINUX32,             # on tannit32, uses 1 core
            APPLVLLINUX64,             # on tannit64, uses 1 core
            #
            JITWIN32,                  # on bigboard
            #JITFREEBSD64,              # on headless
            JITMACOSX64,               # on mvt's machine
            ], branch=None, hour=3, minute=0),

        Nightly("nighly-4-00-py3k", [
            LINUX32,                   # on tannit32, uses 4 cores
            ], branch='py3k', hour=4, minute=0),

    ],

    'status': [status, ircbot],

    'slaves': [BuildSlave(name, password)
               for (name, password)
               in passwords.iteritems()],

    'builders': [
                  {"name": LINUX32,
                   "slavenames": ["cobra", "bigdogvm1", "tannit32"],
                   "builddir": LINUX32,
                   "factory": pypyOwnTestFactory,
                   "category": 'linux32',
                   # this build needs 4 CPUs
                   "locks": [TannitCPU.access('exclusive')],
                  },
                  {"name": LINUX64,
                   "slavenames": ["tannit64"],
                   "builddir": LINUX64,
                   "factory": pypyOwnTestFactory,
                   "category": 'linux64',
                   # this build needs 4 CPUs
                   "locks": [TannitCPU.access('exclusive')],
                  },
                  {"name": APPLVLLINUX32,
                   "slavenames": ["bigdogvm1", "tannit32"],
                   "builddir": APPLVLLINUX32,
                   "factory": pypyTranslatedAppLevelTestFactory,
                   'category': 'linux32',
                   "locks": [TannitCPU.access('counting')],
                  },
                  {"name": APPLVLLINUX64,
                   "slavenames": ["tannit64"],
                   "builddir": APPLVLLINUX64,
                   "factory": pypyTranslatedAppLevelTestFactory64,
                   "category": "linux64",
                   "locks": [TannitCPU.access('counting')],
                  },
                  {"name": OJITLINUX32,
                   "slavenames": ["bigdogvm1", "tannit32"],
                   "builddir": OJITLINUX32,
                   "factory": pypy_OjitTranslatedTestFactory,
                   "category": 'linux32',
                   "locks": [TannitCPU.access('counting')],
                  },
                  {"name" : JITLINUX32,
                   "slavenames": ["bigdogvm1", "tannit32"],
                   'builddir' : JITLINUX32,
                   'factory' : pypyJITTranslatedTestFactory,
                   'category' : 'linux32',
                   "locks": [TannitCPU.access('counting')],
                   },
                  {'name': JITLINUX64,
                   'slavenames': ['tannit64'],
                   'builddir': JITLINUX64,
                   'factory': pypyJITTranslatedTestFactory64,
                   'category': 'linux64',
                   "locks": [TannitCPU.access('counting')],
                  },
                  {"name": JITONLYLINUX32,
                   "slavenames": ["tannit32", "bigdogvm1"],
                   "builddir": JITONLYLINUX32,
                   "factory": pypyJitOnlyOwnTestFactory,
                   "category": 'linux32',
                   "locks": [TannitCPU.access('counting')],
                  },
                  {"name": JITBENCH,
                   "slavenames": ["tannit32"],
                   "builddir": JITBENCH,
                   "factory": pypyJITBenchmarkFactory_tannit,
                   "category": 'benchmark-run',
                   # the locks are acquired with fine grain inside the build
                  },
                  {"name": JITBENCH64,
                   "slavenames": ["tannit64"],
                   "builddir": JITBENCH64,
                   "factory": pypyJITBenchmarkFactory64_tannit,
                   "category": "benchmark-run",
                   # the locks are acquired with fine grain inside the build
                   },
                  {"name": JITBENCH64_2,
                   "slavenames": ["speed-python-64"],
                   "builddir": JITBENCH64_2,
                   "factory": pypyJITBenchmarkFactory64_speed,
                   "category": "benchmark-run",
                   # the locks are acquired with fine grain inside the build
                   },
                  {"name": CPYTHON_64,
                   "slavenames": ["speed-python-64"],
                   "builddir": CPYTHON_64,
                   "factory": cPython27BenchmarkFactory64,
                   "category": "benchmark-run",
                   # the locks are acquired with fine grain inside the build
                   },
                  {"name": MACOSX32,
                   "slavenames": ["minime"],
                   "builddir": MACOSX32,
                   "factory": pypyOwnTestFactory,
                   "category": 'mac32'
                  },
                  {"name": PPCLINUX32,
                   "slavenames": ["stups-ppc32"],
                   "builddir": PPCLINUX32,
                   "factory": pypyOwnTestFactory,
                   "category": 'linuxppc32'
                  },
                  {"name" : JITMACOSX64,
                   "slavenames": ["macmini-mvt", "xerxes"],
                   'builddir' : JITMACOSX64,
                   'factory' : pypyJITTranslatedTestFactoryOSX64,
                   'category' : 'mac64',
                   },
                  {"name": WIN32,
                   "slavenames": ["aurora", "SalsaSalsa", "snakepit32", "bigboard"],
                   "builddir": WIN32,
                   "factory": pypyOwnTestFactoryWin,
                   "category": 'win32'
                  },
                  {"name": WIN64,
                   "slavenames": ["snakepit64"],
                   "builddir": WIN64,
                   "factory": pypyOwnTestFactoryWin,
                   "category": 'win32'
                  },
                  {"name": APPLVLWIN32,
                   "slavenames": ["aurora", "SalsaSalsa", "snakepit32", "bigboard"],
                   "builddir": APPLVLWIN32,
                   "factory": pypyTranslatedAppLevelTestFactoryWin,
                   "category": "win32"
                  },
                  {"name" : JITWIN32,
                   "slavenames": ["aurora", "SalsaSalsa", "snakepit32", "bigboard"],
                   'builddir' : JITWIN32,
                   'factory' : pypyJITTranslatedTestFactoryWin,
                   'category' : 'win32',
                   },
                  {"name" : JITWIN64,
                   "slavenames": ["snakepit64"],
                   'builddir' : JITWIN64,
                   'factory' : pypyJITTranslatedTestFactoryWin,
                   'category' : 'win32',
                   },
                  {"name" : JITFREEBSD64,
                   "slavenames": ['headless'],
                   'builddir' : JITFREEBSD64,
                   'factory' : pypyJITTranslatedTestFactoryFreeBSD,
                   "category": 'freebsd64'
                   },
                ],

    # http://readthedocs.org/docs/buildbot/en/latest/tour.html#debugging-with-manhole
    #'manhole': manhole.PasswordManhole("tcp:1234:interface=127.0.0.1",
    #                                    "buildmaster","XndZopHM"),
    'buildbotURL': 'http://buildbot.pypy.org/',  # with a trailing '/'!
    'projectURL': 'http://pypy.org/',
    'projectName': 'PyPy'}
