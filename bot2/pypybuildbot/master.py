
import os
from buildbot.scheduler import Nightly, Triggerable
from buildbot.schedulers.forcesched import ForceScheduler
from buildbot.schedulers.forcesched import ValidationError
from buildbot.buildslave import BuildSlave
from buildbot.status.html import WebStatus
from buildbot.status.web import authz
from buildbot.process.build import Build
#from buildbot import manhole
from pypybuildbot.pypylist import PyPyList, NumpyStatusList
from pypybuildbot.ircbot import IRC  # side effects
from pypybuildbot.util import we_are_debugging

# Forbid "force build" with empty user name
class CustomForceScheduler(ForceScheduler):
    def force(self, owner, builder_name, **kwargs):
        if not owner:
            raise ValidationError, "Please write your name in the corresponding field."
        return ForceScheduler.force(self, owner, builder_name, **kwargs)

# Forbid "stop build" without a reason that starts with "!"
def _checkStopBuild(self, reason=""):
    if ": !" not in reason:
        raise ValidationError, "Please write a reason that starts with '!'."
    return _baseStopBuild(self, reason)
_baseStopBuild = Build.stopBuild
Build.stopBuild = _checkStopBuild


if we_are_debugging():
    channel = '#buildbot-test'
else:
    channel = '#pypy'

authz_cfg = authz.Authz(pingBuilder=False, forceBuild=True, forceAllBuilds=True,
                        stopBuild=True, stopAllBuilds=True, cancelPendingBuild=True)
# xxx could maybe also say 'default_action=True' instead of all the
# '*=True' in the line above
status = WebStatus(httpPortNumber, authz=authz_cfg)
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

# all ARM buildbot configuration si in arm_master.py
ARM = load('pypybuildbot.arm_master')

TannitCPU = pypybuilds.TannitCPU
WinSlaveLock = pypybuilds.WinSlaveLock
#SpeedOldLock = pypybuilds.SpeedOldLock
Bencher4Lock = pypybuilds.Bencher4Lock

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
pypyTranslatedAppLevelTestFactoryS390X = pypybuilds.Translated(lib_python=True,
                                                               app_tests=True,
                                                               platform='s390x')

# these are like the two above: the only difference is that they only run
# lib-python tests,not -A tests
pypyTranslatedLibPythonTestFactory = pypybuilds.Translated(lib_python=True,
                                                          app_tests=False)
pypyTranslatedLibPythonTestFactory64 = pypybuilds.Translated(lib_python=True,
                                                            app_tests=False,
                                                            platform='linux64')

pypyTranslatedAppLevelTestFactoryWin = pypybuilds.Translated(
    platform="win32",
    lib_python=True,
    app_tests=True,
    )

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
    trigger='NUMPY64_scheduler',
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
    translationArgs=jit_translation_args + ['--make-jobs=1'],
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
    )

pypyJITTranslatedTestFactoryWin = pypybuilds.Translated(
    platform="win32",
    translationArgs=jit_translation_args,
    targetArgs=[],
    lib_python=True,
    pypyjit=True,
    app_tests=True,
    trigger='NUMPYWIN_scheduler',
    )

pypyJITTranslatedTestFactoryFreeBSD = pypybuilds.Translated(
    platform="freebsd64",
    translationArgs=jit_translation_args,
    targetArgs=[],
    lib_python=True,
    pypyjit=True,
    app_tests=True,
    )

pypyJITTranslatedTestFactoryS390X = pypybuilds.Translated(
    platform='s390x',
    translationArgs=jit_translation_args,
    targetArgs=[],
    lib_python=True,
    pypyjit=True,
    app_tests=True)

pypyJITBenchmarkFactory_tannit = pypybuilds.JITBenchmark(host='tannit')
pypyJITBenchmarkFactory64_tannit = pypybuilds.JITBenchmark(platform='linux64',
                                                           host='tannit',
                                                           postfix='-64')
pypyJITBenchmarkFactory64_speed = pypybuilds.JITBenchmarkSingleRun(
    platform='linux64',
    host='speed_python',
    postfix='-64')

pypyNumpyCompatability = pypybuilds.NativeNumpyTests(platform='linux64')
pypyNumpyCompatabilityWin = pypybuilds.NativeNumpyTests(platform='win32')

#

LINUX32 = "own-linux-x86-32"
LINUX64 = "own-linux-x86-64"
LINUX_S390X = "own-linux-s390x"

MACOSX32 = "own-macosx-x86-32"
WIN32 = "own-win-x86-32"
APPLVLLINUX32 = "pypy-c-app-level-linux-x86-32"
APPLVLLINUX64 = "pypy-c-app-level-linux-x86-64"
APPLVLWIN32 = "pypy-c-app-level-win-x86-32"

LIBPYTHON_LINUX32 = "pypy-c-lib-python-linux-x86-32"
LIBPYTHON_LINUX64 = "pypy-c-lib-python-linux-x86-64"

JITLINUX32 = "pypy-c-jit-linux-x86-32"
JITLINUX64 = "pypy-c-jit-linux-x86-64"
JITLINUX_S390X = 'pypy-c-jit-linux-s390x'
JITMACOSX64 = "pypy-c-jit-macosx-x86-64"
#JITMACOSX64_2 = "pypy-c-jit-macosx-x86-64-2"
JITWIN32 = "pypy-c-jit-win-x86-32"

JITONLYLINUXPPC64 = "jitonly-own-linux-ppc-64"
JITBENCH = "jit-benchmark-linux-x86-32"
JITBENCH64 = "jit-benchmark-linux-x86-64"
CPYTHON_64 = "cpython-2-benchmark-x86-64"
NUMPY_64 = "numpy-compatibility-linux-x86-64"
NUMPY_WIN = "numpy-compatibility-win-x86-32"

# buildbot builder
PYPYBUILDBOT = 'pypy-buildbot'
JITFREEBSD964 = 'pypy-c-jit-freebsd-9-x86-64'

WIN64 = "own-win-x86-64"
INDIANA32 = "own-indiana-x86-32"
JITWIN64 = "pypy-c-jit-win-x86-64"
JITFREEBSD764 = 'pypy-c-jit-freebsd-7-x86-64'
JITFREEBSD864 = 'pypy-c-jit-freebsd-8-x86-64'
JITINDIANA32 = "pypy-c-jit-indiana-x86-32"
JITBENCH64_NEW = 'jit-benchmark-linux-x86-64-single-run'
inactive_slaves = [
                  {"name": WIN64,
                   "slavenames": [],
                   "builddir": WIN64,
                   "factory": pypyOwnTestFactoryWin,
                   "category": 'win32'
                  },
                  {'name': INDIANA32,
                   'slavenames': [],
                   'builddir': INDIANA32,
                   'factory': pypyOwnTestFactoryIndiana,
                   'category': 'openindiana32',
                   },
                  {"name" : JITWIN64,
                   "slavenames": [],
                   'builddir' : JITWIN64,
                   'factory' : pypyJITTranslatedTestFactoryWin,
                   'category' : 'win32',
                   },
                  {"name" : JITFREEBSD764,
                   "slavenames": [],
                   'builddir' : JITFREEBSD764,
                   'factory' : pypyJITTranslatedTestFactoryFreeBSD,
                   "category": 'freebsd64'
                   },
                  {"name": JITFREEBSD864,
                   "slavenames": [],
                   'builddir' : JITFREEBSD864,
                   'factory' : pypyJITTranslatedTestFactoryFreeBSD,
                   "category": 'freebsd64'
                   },
                  # openindiana
                  {'name': JITINDIANA32,
                   'slavenames': [],
                   'builddir': JITINDIANA32,
                   'factory': pypyJITTranslatedTestFactoryIndiana,
                   'category': 'openindiana32',
                   },
                   ]
extra_opts = {'xerxes': {'keepalive_interval': 15},
             'aurora': {'max_builds': 1},
             'salsa': {'max_builds': 1},
             'hhu-raspberry-pi': {'max_builds': 1},
             'hhu-pypy-pi': {'max_builds': 1},
             'hhu-pypy-pi2': {'max_builds': 1},
             }

BuildmasterConfig = {
    'slavePortnum': slavePortnum,

    'change_source': [],

    'schedulers': [
        # the benchmarks run on tannit and (planned) speed-old.python.org.
        # All the other linux tests run on bencher4.soft-dev.org.
        Nightly("nightly-0-00", [
            # linux tests
            LINUX32,                   # on tannit32, uses all cores
            LINUX64,                   # on bencher4, uses all cores
            JITLINUX32,                # on tannit32, uses 1 core
            JITLINUX64,                # on bencher4, uses 1 core
            #APPLVLLINUX32,            # on tannit32, uses 1 core
            #APPLVLLINUX64,             # on bencher4, uses 1 core
            # other platforms
            #MACOSX32,                 # on minime
            JITWIN32,                  # on allegro_win32, SalsaSalsa
            WIN32,                     # on allegro_win32, SalsaSalsa
            #JITFREEBSD764,            # on headless
            #JITFREEBSD864,            # on ananke
            JITFREEBSD964,             # on tavendo
            JITMACOSX64,               # on xerxes
            # buildbot selftest
            PYPYBUILDBOT               # on bencher4
            ], branch='default', hour=0, minute=0),

        Nightly("nightly-1-00", [
            JITBENCH,                  # on tannit32, uses 1 core (in part exclusively)
            JITBENCH64,                # on tannit64, uses 1 core (in part exclusively)
            #JITBENCH64_NEW,            # on speed64, uses 1 core (in part exclusively)

        ], branch=None, hour=5, minute=0),

        Triggerable("NUMPY64_scheduler", [
            NUMPY_64,                  # on tannit64, uses 1 core, takes about 5min.
        ]),

        Triggerable("NUMPYWIN_scheduler", [
            NUMPY_WIN,                  # on allegro_win32, SalsaSalsa
        ]),

        #Nightly("nightly-3-01-py3.5", [LINUX64, JITLINUX64,],
        #        branch="py3.5", hour=3, minute=0),

        Nightly("nightly-3-00-py3.5", [
            LINUX32,                   # on tannit32, uses all cores
            JITLINUX32,                # on tannit32, uses 1 core
            LINUX64,                   # on bencher4, uses all cores
            JITLINUX64,                # on bencher4, uses 1 core
            JITMACOSX64,               # on xerxes
            JITWIN32,                  # on allegro_win32, SalsaSalsa
            ], branch="py3.5", hour=3, minute=0),

        # S390X vm (ibm-research)
        Nightly("nightly-4-00", [LINUX_S390X], branch='default', hour=0, minute=0),
        Nightly("nightly-4-01", [JITLINUX_S390X], branch='default', hour=2, minute=0),

        # this one has faithfully run every night even though the latest
        # change to that branch was in January 2013.  Re-enable one day.
        #Nightly("nighly-ppc", [
        #    JITONLYLINUXPPC64,         # on gcc1
        #    ], branch='ppc-jit-backend', hour=1, minute=0),

        CustomForceScheduler('Force Scheduler',
            builderNames=[
                        PYPYBUILDBOT,
                        LINUX32,
                        LINUX64,

                        MACOSX32,
                        WIN32,
                        APPLVLLINUX32,
                        APPLVLLINUX64,
                        APPLVLWIN32,

                        LIBPYTHON_LINUX32,
                        LIBPYTHON_LINUX64,

                        JITLINUX32,
                        JITLINUX64,
                        JITMACOSX64,
                        JITWIN32,
                        JITFREEBSD964,

                        JITONLYLINUXPPC64,
                        JITBENCH,
                        JITBENCH64,
                        JITBENCH64_NEW,
                        NUMPY_64,
                        NUMPY_WIN,
                        #INDIANA32,
                        #WIN64,
                        #JITMACOSX64_2,
                        #JITWIN64,
                        #JITFREEBSD764,
                        #JITFREEBSD864,
                        #JITINDIANA32,

                        LINUX_S390X,
                        JITLINUX_S390X,

            ] + ARM.builderNames, properties=[]),
    ] + ARM.schedulers,

    'status': [status, ircbot],

    'slaves': [BuildSlave(name, password, **extra_opts.get(name, {}))
               for (name, password)
               in passwords.iteritems()],

    'builders': [
                  {"name": LINUX32,
                   "slavenames": ["tannit32"],
                   "builddir": LINUX32,
                   "factory": pypyOwnTestFactory,
                   "category": 'linux32',
                   "locks": [TannitCPU.access('counting')],
                  },
                  {"name": LINUX64,
                   #"slavenames": ["bencher4", "speed-old"],
                   "slavenames": ["bencher4"],
                   "builddir": LINUX64,
                   "factory": pypyOwnTestFactory,
                   "category": 'linux64',
                   "locks": [Bencher4Lock.access('counting')],
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
                   #"slavenames": ["bencher4", "speed-old"],
                   "slavenames": ["bencher4"],
                   "builddir": APPLVLLINUX64,
                   "factory": pypyTranslatedAppLevelTestFactory64,
                   "category": "linux64",
                   "locks": [Bencher4Lock.access('counting')],
                  },
                  {"name": LIBPYTHON_LINUX32,
                   "slavenames": ["tannit32"],
                   #"slavenames": ["allegro32"],
                   "builddir": LIBPYTHON_LINUX32,
                   "factory": pypyTranslatedLibPythonTestFactory,
                   'category': 'linux32',
                   "locks": [TannitCPU.access('counting')],
                  },
                  {"name": LIBPYTHON_LINUX64,
                   #"slavenames": ["bencher4", "speed-old"],
                   "slavenames": ["bencher4"],
                   "builddir": LIBPYTHON_LINUX64,
                   "factory": pypyTranslatedLibPythonTestFactory,
                   "category": "linux64",
                   "locks": [Bencher4Lock.access('counting')],
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
                   #'slavenames': ["bencher4", "speed-old"],
                   'slavenames': ["bencher4"],
                   'builddir': JITLINUX64,
                   'factory': pypyJITTranslatedTestFactory64,
                   'category': 'linux64',
                   "locks": [Bencher4Lock.access('counting')],
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
                   {"name": JITBENCH64_NEW,
                    "slavenames": ['speed-old'],
                    "builddir": JITBENCH64_NEW,
                    "factory": pypyJITBenchmarkFactory64_speed,
                    "category": "benchmark-run",
                    "locks": [Bencher4Lock.access('exclusive')],
                    },
                  {"name": MACOSX32,
                   "slavenames": ["minime"],
                   "builddir": MACOSX32,
                   "factory": pypyOwnTestFactoryOSX32,
                   "category": 'mac32'
                  },
                  {"name" : JITMACOSX64,
                   "slavenames": ["rebuy-de", "tosh", "osx-10.9-x64-dw"],  # "xerxes"
                   'builddir' : JITMACOSX64,
                   'factory' : pypyJITTranslatedTestFactoryOSX64,
                   'category' : 'mac64',
                   },
                  #{"name" : JITMACOSX64_2,
                  # "slavenames": ["rebuy-de", "xerxes", "tosh"],
                  # 'builddir' : JITMACOSX64_2,
                  # 'factory' : pypyJITTranslatedTestFactoryOSX64,
                  # 'category' : 'mac64',
                  # },
                  {"name": WIN32,
                   "slavenames": ["SalsaSalsa", "allegro_win32", "anubis64"],
                   "builddir": WIN32,
                   "factory": pypyOwnTestFactoryWin,
                   "locks": [WinSlaveLock.access('counting')],
                   "category": 'win32',
                  },
                 {"name": APPLVLWIN32,
                   "slavenames": ["SalsaSalsa", "allegro_win32"],
                   "builddir": APPLVLWIN32,
                   "factory": pypyTranslatedAppLevelTestFactoryWin,
                   "locks": [WinSlaveLock.access('counting')],
                   "category": "win32",
                  },
                  {"name" : JITWIN32,
                   "slavenames": ["SalsaSalsa", "allegro_win32", "anubis64"],
                   'builddir' : JITWIN32,
                   'factory' : pypyJITTranslatedTestFactoryWin,
                   "locks": [WinSlaveLock.access('counting')],
                   'category' : 'win32',
                   },
                  {"name" : JITFREEBSD964,
                   "slavenames": ['hybridlogic', 'tavendo-freebsd-9.2-amd64'],
                   'builddir' : JITFREEBSD964,
                   'factory' : pypyJITTranslatedTestFactoryFreeBSD,
                   "category": 'freebsd64'
                   },
                  # PPC
                  {"name": JITONLYLINUXPPC64,
                   "slavenames": ['gcc1'],
                   "builddir": JITONLYLINUXPPC64,
                   "factory": pypyJitOnlyOwnTestFactory,
                   "category": 'linux-ppc64',
                   },
                  {'name': NUMPY_64,
                   'slavenames': ["bencher4"],
                   #'slavenames': ["tannit64"],
                   'builddir': NUMPY_64,
                   'factory': pypyNumpyCompatability,
                   'category': 'numpy',
                   #'locks': [TannitCPU.access('counting')],
                   "locks": [Bencher4Lock.access('counting')],
                  },
                  {'name': NUMPY_WIN,
                   'slavenames': ["allegro_win32", "SalsaSalsa"],
                   'builddir': NUMPY_WIN,
                   'factory': pypyNumpyCompatabilityWin,
                   "locks": [WinSlaveLock.access('counting')],
                   'category': 'numpy',
                  },
                  {'name': PYPYBUILDBOT,
                   'slavenames': ['bencher4'],
                   'builddir': PYPYBUILDBOT,
                   'factory': pypybuilds.PyPyBuildbotTestFactory(),
                   'category': 'buildbot',
                   "locks": [Bencher4Lock.access('counting')],
                  },
                  # S390X
                  {"name": LINUX_S390X,
                   "slavenames": ["s390x-slave"],
                   "builddir": LINUX_S390X,
                   "factory": pypyOwnTestFactory,
                   "category": 'linux-s390x',
                  },
                  {'name': JITLINUX_S390X,
                   'slavenames': ['s390x-slave'],
                   'builddir': JITLINUX_S390X,
                   'factory': pypyJITTranslatedTestFactoryS390X,
                   'category': 'linux-s390x',
                  },
                ] + ARM.builders,

    # http://readthedocs.org/docs/buildbot/en/latest/tour.html#debugging-with-manhole
    #'manhole': manhole.PasswordManhole("tcp:1234:interface=127.0.0.1",
    #                                    "buildmaster","XndZopHM"),
    'buildbotURL': 'http://buildbot.pypy.org/',  # with a trailing '/'!
    'projectURL': 'http://pypy.org/',
    'projectName': 'PyPy',
    'logMaxSize': 5*1024*1204, # 5M
    }
