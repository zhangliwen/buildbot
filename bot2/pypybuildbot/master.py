
import os
import getpass
from buildbot.scheduler import Nightly, Triggerable
from buildbot.buildslave import BuildSlave
from buildbot.status.html import WebStatus
from buildbot.process.builder import Builder
#from buildbot import manhole
from pypybuildbot.pypylist import PyPyList, NumpyStatusList
from pypybuildbot.ircbot import IRC # side effects
from pypybuildbot.util import we_are_debugging

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

if we_are_debugging():
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
WinLockCPU = pypybuilds.WinLockCPU
ARMCrossLock = pypybuilds.ARMCrossLock
ARMBoardLock = pypybuilds.ARMBoardLock
ARMXdistLock = pypybuilds.ARMXdistLock

pypyOwnTestFactory = pypybuilds.Own()
pypyOwnTestFactoryWin = pypybuilds.Own(platform="win32")
pypyOwnTestFactoryIndiana = pypybuilds.Own(platform="indiana32")
pypyJitOnlyOwnTestFactory = pypybuilds.Own(cherrypick="jit")

# OSX 32bit tests require a larger timeout to finish
pypyOwnTestFactoryOSX32 = pypybuilds.Own(timeout=3*3600)

pypyTranslatedAppLevelTestFactory = pypybuilds.Translated(lib_python=True,
                                                          app_tests=True)
pypyTranslatedAppLevelTestFactory64 = pypybuilds.Translated(lib_python=True,
                                                            app_tests=True,
                                                            platform='linux64')

# these are like the two above: the only difference is that they only run
# lib-python tests,not -A tests
pypyTranslatedLibPythonTestFactory = pypybuilds.Translated(lib_python=True,
                                                          app_tests=False)
pypyTranslatedLibPythonTestFactory64 = pypybuilds.Translated(lib_python=True,
                                                            app_tests=False,
                                                            platform='linux64')


pypyTranslatedAppLevelTestFactoryPPC64 = pypybuilds.Translated(
        lib_python=True,
        app_tests=True,
        platform='linux-ppc64',
        interpreter='python')

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

pypyJITTranslatedTestFactoryPPC64 = pypybuilds.Translated(
    translationArgs=jit_translation_args,
    targetArgs=[],
    lib_python=True,
    pypyjit=True,
    app_tests=True,
    platform='linux-ppc64',
    interpreter='python',
    )

pypyJITTranslatedTestFactoryIndiana = pypybuilds.Translated(
    translationArgs=jit_translation_args,
    targetArgs=[],
    lib_python=True,
    pypyjit=True,
    app_tests=True,
    platform='openindiana32',
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


# ARM own test factories
crosstranslationargs = ['--platform=arm', '--gcrootfinder=shadowstack']
crosstranslationjitargs = ['--jit-backend=arm']
# this one needs a larger timeout due to how it is run
pypyJitBackendOnlyOwnTestFactoryARM = pypybuilds.Own(
        cherrypick=':'.join(["jit/backend/arm",
                            "jit/backend/llsupport",
                            "jit/backend/test",  # kill this one in case it is too slow
                            ]),
        timeout=6 * 3600)
pypyJitOnlyOwnTestFactoryARM = pypybuilds.Own(cherrypick="jit", timeout=2 * 3600)
pypyOwnTestFactoryARM = pypybuilds.Own(timeout=2*3600)
pypyCrossTranslationFactoryARM = pypybuilds.NightlyBuild(
    translationArgs=crosstranslationargs+['-O2'],
    platform='linux-armel',
    interpreter='pypy',
    trigger='APPLVLLINUXARM_scheduler')

pypyJITCrossTranslationFactoryARM = pypybuilds.NightlyBuild(
    translationArgs=(crosstranslationargs
                        + jit_translation_args
                        + crosstranslationjitargs),
    platform='linux-armel',
    interpreter='pypy',
    trigger='JITLINUXARM_scheduler')

pypyARMJITTranslatedTestFactory = pypybuilds.TranslatedTests(
    translationArgs=(crosstranslationargs
                        + jit_translation_args
                        + crosstranslationjitargs),
    lib_python=True,
    pypyjit=True,
    app_tests=True,
    platform='linux-armel',
    )
pypyARMTranslatedAppLevelTestFactory = pypybuilds.TranslatedTests(
    translationArgs=crosstranslationargs+['-O2'],
    lib_python=True,
    app_tests=True,
    platform='linux-armel',
)
#

LINUX32 = "own-linux-x86-32"
LINUX64 = "own-linux-x86-64"
LINUXPPC64 = "own-linux-ppc-64"
INDIANA32 = "own-indiana-x86-32"

MACOSX32 = "own-macosx-x86-32"
WIN32 = "own-win-x86-32"
WIN64 = "own-win-x86-64"
APPLVLLINUX32 = "pypy-c-app-level-linux-x86-32"
APPLVLLINUX64 = "pypy-c-app-level-linux-x86-64"
APPLVLLINUXARM = "pypy-c-app-level-linux-armel"
APPLVLLINUXPPC64 = "pypy-c-app-level-linux-ppc-64"
APPLVLWIN32 = "pypy-c-app-level-win-x86-32"

LIBPYTHON_LINUX32 = "pypy-c-lib-python-linux-x86-32"
LIBPYTHON_LINUX64 = "pypy-c-lib-python-linux-x86-64"

JITLINUX32 = "pypy-c-jit-linux-x86-32"
JITLINUX64 = "pypy-c-jit-linux-x86-64"
JITLINUXARM = "pypy-c-jit-linux-armel"
JITLINUXPPC64 = "pypy-c-jit-linux-ppc-64"
OJITLINUX32 = "pypy-c-Ojit-no-jit-linux-x86-32"
JITMACOSX64 = "pypy-c-jit-macosx-x86-64"
JITWIN32 = "pypy-c-jit-win-x86-32"
JITWIN64 = "pypy-c-jit-win-x86-64"
JITFREEBSD64 = 'pypy-c-jit-freebsd-7-x86-64'
JITINDIANA32 = "pypy-c-jit-indiana-x86-32"

JITBACKENDONLYLINUXARMEL = "jitbackendonly-own-linux-armel"
JITBACKENDONLYLINUXARMELXDIST = "jitbackendonly-own-linux-armel-xdist"
JITONLYLINUXPPC64 = "jitonly-own-linux-ppc-64"
JITBENCH = "jit-benchmark-linux-x86-32"
JITBENCH64 = "jit-benchmark-linux-x86-64"
JITBENCH64_2 = 'jit-benchmark-linux-x86-64-2'
CPYTHON_64 = "cpython-2-benchmark-x86-64"

# build only
BUILDLINUXARM = "build-pypy-c-linux-armel"
BUILDJITLINUXARM = "build-pypy-c-jit-linux-armel"

BuildmasterConfig = {
    'slavePortnum': slavePortnum,

    'change_source': [],

    'schedulers': [
        # the benchmarks run on tannit and speed.python.org.
        # All the other linux tests run on allegro
        Nightly("nightly-0-00", [
            # benchmarks
            JITBENCH,                  # on tannit32, uses 1 core (in part exclusively)
            JITBENCH64,                # on tannit64, uses 1 core (in part exclusively)
            JITBENCH64_2,              # on speed.python.org, uses 1 core (in part exclusively)
            CPYTHON_64,                # on speed.python.org, uses 1 core (in part exclusively)
            # linux tests
            LINUX32,                   # on allegro32, uses 20 (twenty!) core 
            # other platforms
            MACOSX32,                  # on minime
            JITWIN32,                  # on aurora
            JITFREEBSD64,              # on headless
            JITMACOSX64,               # on mvt's machine
            ], branch=None, hour=0, minute=0),

        Nightly("nightly-0-45", [
            LINUX64,                   # on allegro64, uses 20 (twenty!) cores
            ], branch=None, hour=0, minute=45),

        Nightly("nightly-1-30-py3k", [
            LINUX32,                   # on allegro64, uses 20 (twenty!) cores
            ], branch="py3k", hour=1, minute=30),

        Nightly("nightly-2-15-py3k", [
            LINUX64,                   # on allegro64, uses 20 (twenty!) cores
            ], branch="py3k", hour=2, minute=15),

        Nightly("nightly-3-00", [
            JITLINUX32,                # on allegro32, uses 1 core
            JITLINUX64,                # on allegro64, uses 1 core
            OJITLINUX32,               # on allegro32, uses 1 core
            APPLVLLINUX32,             # on allegro32, uses 1 core
            APPLVLLINUX64,             # on allegro64, uses 1 core
            ], branch=None, hour=3, minute=0),

        Nightly("nightly-4-00-py3k", [
            APPLVLLINUX32,             # on allegro32, uses 1 core
            #APPLVLLINUX64,             # on allegro64, uses 1 core
            ], branch="py3k", hour=4, minute=0),

        #
        Nightly("nighly-ppc", [
            JITONLYLINUXPPC64,         # on gcc1
            ], branch='ppc-jit-backend', hour=1, minute=0),
        # 
        Nightly("nighly-arm-0-00", [
            BUILDLINUXARM,                 # on hhu-cross-armel, uses 1 core
            BUILDJITLINUXARM,              # on hhu-cross-armel, uses 1 core
            JITBACKENDONLYLINUXARMEL,      # on hhu-beagleboard or hhu-imx.53
            ], branch=None, hour=0, minute=0),
        #
        Triggerable("APPLVLLINUXARM_scheduler", [
            APPLVLLINUXARM,            # triggered by BUILDLINUXARM, on hhu-beagleboard or hhu-imx.53
	]),
        Triggerable("JITLINUXARM_scheduler", [
            JITLINUXARM,               # triggered by BUILDJITLINUXARM, on hhu-beagleboard or hhu-imx.53
        ]),
    ],

    'status': [status, ircbot],

    'slaves': [BuildSlave(name, password)
               for (name, password)
               in passwords.iteritems()],

    'builders': [
                  {"name": LINUX32,
                   "slavenames": ["tannit32"],
                   "builddir": LINUX32,
                   "factory": pypyOwnTestFactory,
                   "category": 'linux32',
                   # this build needs 4 CPUs
                   "locks": [TannitCPU.access('exclusive')],
                  },
                  {"name": LINUX64,
                   "slavenames": ["allegro64"],
                   "builddir": LINUX64,
                   "factory": pypyOwnTestFactory,
                   "category": 'linux64',
                   # this build needs 4 CPUs
                   #"locks": [TannitCPU.access('exclusive')],
                  },
                  {"name": APPLVLLINUX32,
                   #"slavenames": ["allegro32"],
                   "slavenames": ["tannit32"],
                   "builddir": APPLVLLINUX32,
                   "factory": pypyTranslatedAppLevelTestFactory,
                   'category': 'linux32',
                   "locks": [TannitCPU.access('counting')],
                  },
                  {"name": APPLVLLINUX64,
                   "slavenames": ["allegro64"],
                   "builddir": APPLVLLINUX64,
                   "factory": pypyTranslatedAppLevelTestFactory64,
                   "category": "linux64",
                   #"locks": [TannitCPU.access('counting')],
                  },
                  {"name": LIBPYTHON_LINUX32,
                   "slavenames": ["tannit32"],
#                   "slavenames": ["allegro32"],
                   "builddir": LIBPYTHON_LINUX32,
                   "factory": pypyTranslatedLibPythonTestFactory,
                   'category': 'linux32',
                   "locks": [TannitCPU.access('counting')],
                  },
                  {"name": LIBPYTHON_LINUX64,
                   "slavenames": ["allegro64"],
                   "builddir": LIBPYTHON_LINUX64,
                   "factory": pypyTranslatedLibPythonTestFactory,
                   "category": "linux64",
                   #"locks": [TannitCPU.access('counting')],
                  },                  
                  {"name": OJITLINUX32,
                   "slavenames": ["allegro32"],
                   "builddir": OJITLINUX32,
                   "factory": pypy_OjitTranslatedTestFactory,
                   "category": 'linux32',
                   #"locks": [TannitCPU.access('counting')],
                  },
                  {"name" : JITLINUX32,
                   #"slavenames": ["allegro32"],
                   "slavenames": ["tannit32"],
                   'builddir' : JITLINUX32,
                   'factory' : pypyJITTranslatedTestFactory,
                   'category' : 'linux32',
                   "locks": [TannitCPU.access('counting')],
                   },
                  {'name': JITLINUX64,
                   'slavenames': ["allegro64"],
                   'builddir': JITLINUX64,
                   'factory': pypyJITTranslatedTestFactory64,
                   'category': 'linux64',
                   #"locks": [TannitCPU.access('counting')],
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
                   "factory": pypyOwnTestFactoryOSX32,
                   "category": 'mac32'
                  },
                  {"name" : JITMACOSX64,
                   "slavenames": ["joushou-slave"],
                   'builddir' : JITMACOSX64,
                   'factory' : pypyJITTranslatedTestFactoryOSX64,
                   'category' : 'mac64',
                   },
                  {"name": WIN32,
                   "slavenames": ["tannit-win32", "aurora"],
                   "builddir": WIN32,
                   "factory": pypyOwnTestFactoryWin,
                   "category": 'win32',
                   "locks": [TannitCPU.access('counting')],
                  },
                  {"name": WIN64,
                   "slavenames": ["snakepit64"],
                   "builddir": WIN64,
                   "factory": pypyOwnTestFactoryWin,
                   "category": 'win32'
                  },
                  {"name": APPLVLWIN32,
                   "slavenames": ["tannit-win32", "aurora"],
                   "builddir": APPLVLWIN32,
                   "factory": pypyTranslatedAppLevelTestFactoryWin,
                   "category": "win32",
                   "locks": [TannitCPU.access('counting')],
                  },
                  {"name" : JITWIN32,
                   "slavenames": ["tannit-win32", "aurora"],
                   'builddir' : JITWIN32,
                   'factory' : pypyJITTranslatedTestFactoryWin,
                   'category' : 'win32',
                   "locks": [WinLockCPU.access('exclusive')],
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
                  # PPC
                  {"name": LINUXPPC64,
                   "slavenames": ["gcc1"],
                   "builddir": LINUXPPC64,
                   "factory": pypyOwnTestFactory,
                   "category": 'linux-ppc64',
                   },
                  {"name": JITONLYLINUXPPC64,
                   "slavenames": ['gcc1'],
                   "builddir": JITONLYLINUXPPC64,
                   "factory": pypyJitOnlyOwnTestFactory,
                   "category": 'linux-ppc64',
                   },
                  {"name": APPLVLLINUXPPC64,
                   "slavenames": ["gcc1"],
                   "builddir": APPLVLLINUXPPC64,
                   "factory": pypyTranslatedAppLevelTestFactoryPPC64,
                   "category": "linux-ppc64",
                   },
                  {'name': JITLINUXPPC64,
                   'slavenames': ['gcc1'],
                   'builddir': JITLINUXPPC64,
                   'factory': pypyJITTranslatedTestFactoryPPC64,
                   'category': 'linux-ppc64',
                   },
                  # openindiana
                  {'name': JITINDIANA32,
                   'slavenames': ['jcea-openindiana-32'],
                   'builddir': JITINDIANA32,
                   'factory': pypyJITTranslatedTestFactoryIndiana,
                   'category': 'openindiana32',
                   },
                  {'name': INDIANA32,
                   'slavenames': ['jcea-openindiana-32'],
                   'builddir': INDIANA32,
                   'factory': pypyOwnTestFactoryIndiana,
                   'category': 'openindiana32',
                   },
                  # ARM
                  # armel
                  {"name": JITBACKENDONLYLINUXARMELXDIST,
                   "slavenames": ['hhu-arm'],
                   "builddir": JITBACKENDONLYLINUXARMELXDIST ,
                   "factory": pypyJitBackendOnlyOwnTestFactoryARM,
                   "category": 'linux-armel',
                   "locks": [ARMXdistLock.access('exclusive'), ARMBoardLock.access('counting')],
                   },
                  {"name": JITBACKENDONLYLINUXARMEL,
                   "slavenames": ['hhu-i.mx53'],
                   "builddir": JITBACKENDONLYLINUXARMEL,
                   "factory": pypyJitBackendOnlyOwnTestFactoryARM,
                   "category": 'linux-armel',
                   "locks": [ARMXdistLock.access('counting'), ARMBoardLock.access('counting')],
                   },
                  # app level builders
                  {"name": APPLVLLINUXARM,
                   "slavenames": ["hhu-beagleboard"],
                   "builddir": APPLVLLINUXARM,
                   "factory": pypyARMTranslatedAppLevelTestFactory,
                   "category": "linux-armel",
                   "locks": [ARMXdistLock.access('counting'), ARMBoardLock.access('counting')],
                   },
                  {"name": JITLINUXARM,
                   "slavenames": ["hhu-beagleboard"],
                   'builddir': JITLINUXARM,
                   'factory': pypyARMJITTranslatedTestFactory ,
                   'category': 'linux-armel',
                   "locks": [ARMXdistLock.access('counting'), ARMBoardLock.access('counting')],
                   },
                  # Translation Builders for ARM
                  {"name": BUILDLINUXARM,
                   "slavenames": ['hhu-cross-armel'],
                   "builddir": BUILDLINUXARM,
                   "factory": pypyCrossTranslationFactoryARM,
                   "category": 'linux-armel',
                   "locks": [ARMCrossLock.access('counting')],
                   },
                  {"name": BUILDJITLINUXARM,
                   "slavenames": ['hhu-cross-armel'],
                   "builddir": BUILDJITLINUXARM,
                   "factory": pypyJITCrossTranslationFactoryARM,
                   "category": 'linux-armel',
                   "locks": [ARMCrossLock.access('counting')],
                  },
                ],

    # http://readthedocs.org/docs/buildbot/en/latest/tour.html#debugging-with-manhole
    #'manhole': manhole.PasswordManhole("tcp:1234:interface=127.0.0.1",
    #                                    "buildmaster","XndZopHM"),
    'buildbotURL': 'http://buildbot.pypy.org/',  # with a trailing '/'!
    'projectURL': 'http://pypy.org/',
    'projectName': 'PyPy'}
