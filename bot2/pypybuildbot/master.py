
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

# all ARM buildbot configuration si in arm_master.py
ARM = load('pypybuildbot.arm_master')

TannitCPU = pypybuilds.TannitCPU
#WinLockCPU = pypybuilds.WinLockCPU

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
    )

pypyJITTranslatedTestFactoryFreeBSD = pypybuilds.Translated(
    platform="freebsd64",
    translationArgs=jit_translation_args,
    targetArgs=[],
    lib_python=True,
    pypyjit=True,
    app_tests=True,
    )

pypyJITBenchmarkFactory_tannit = pypybuilds.JITBenchmark()
pypyJITBenchmarkFactory64_tannit = pypybuilds.JITBenchmark(platform='linux64',
                                                           postfix='-64')

#

LINUX32 = "own-linux-x86-32"
LINUX64 = "own-linux-x86-64"
INDIANA32 = "own-indiana-x86-32"

MACOSX32 = "own-macosx-x86-32"
WIN32 = "own-win-x86-32"
WIN64 = "own-win-x86-64"
APPLVLLINUX32 = "pypy-c-app-level-linux-x86-32"
APPLVLLINUX64 = "pypy-c-app-level-linux-x86-64"
APPLVLWIN32 = "pypy-c-app-level-win-x86-32"

LIBPYTHON_LINUX32 = "pypy-c-lib-python-linux-x86-32"
LIBPYTHON_LINUX64 = "pypy-c-lib-python-linux-x86-64"

JITLINUX32 = "pypy-c-jit-linux-x86-32"
JITLINUX64 = "pypy-c-jit-linux-x86-64"
JITMACOSX64 = "pypy-c-jit-macosx-x86-64"
JITWIN32 = "pypy-c-jit-win-x86-32"
JITWIN64 = "pypy-c-jit-win-x86-64"
JITFREEBSD764 = 'pypy-c-jit-freebsd-7-x86-64'
JITFREEBSD864 = 'pypy-c-jit-freebsd-8-x86-64'
JITFREEBSD964 = 'pypy-c-jit-freebsd-9-x86-64'
JITINDIANA32 = "pypy-c-jit-indiana-x86-32"

JITONLYLINUXPPC64 = "jitonly-own-linux-ppc-64"
JITBENCH = "jit-benchmark-linux-x86-32"
JITBENCH64 = "jit-benchmark-linux-x86-64"
JITBENCH64_2 = 'jit-benchmark-linux-x86-64-2'
CPYTHON_64 = "cpython-2-benchmark-x86-64"


extra_opts= {'xerxes': {'keepalive_interval': 15},
             'aurora': {'max_builds': 1},
             'salsa': {'max_builds': 1},
             }

BuildmasterConfig = {
    'slavePortnum': slavePortnum,

    'change_source': [],

    'schedulers': [
        # the benchmarks run on tannit and speed.python.org.
        # All the other linux tests run on allegro
        Nightly("nightly-0-00", [
            # benchmarks
            # linux tests
            LINUX32,                   # on tannit32, uses all cores
            LINUX64,                   # on allegro64, uses all cores
            JITLINUX32,                # on tannit32, uses 1 core
            JITLINUX64,                # on allegro64, uses 1 core
            APPLVLLINUX32,             # on tannit32, uses 1 core
            APPLVLLINUX64,             # on allegro64, uses 1 core
            # other platforms
            MACOSX32,                  # on minime
            JITWIN32,                  # on aurora
            JITFREEBSD764,             # on headless
            JITFREEBSD864,             # on ananke
            JITFREEBSD964,             # on exarkun's freebsd
            JITMACOSX64,               # on xerxes
            ], branch=None, hour=0, minute=0),

        Nightly("nightly-2-00", [
            JITBENCH,                  # on tannit32, uses 1 core (in part exclusively)
            JITBENCH64,                # on tannit64, uses 1 core (in part exclusively)
        ], branch=None, hour=2, minute=0),

        Nightly("nightly-2-00-py3k", [
            LINUX64,                   # on allegro64, uses all cores
            APPLVLLINUX64,             # on allegro64, uses 1 core
            ], branch="py3k", hour=2, minute=0),

        Nightly("nighly-ppc", [
            JITONLYLINUXPPC64,         # on gcc1
            ], branch='ppc-jit-backend', hour=1, minute=0),
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
                   "slavenames": ["allegro64"],
                   "builddir": LINUX64,
                   "factory": pypyOwnTestFactory,
                   "category": 'linux64',
                   #"locks": [TannitCPU.access('counting')],
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
                   #"slavenames": ["allegro32"],
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
                  {"name": MACOSX32,
                   "slavenames": ["minime"],
                   "builddir": MACOSX32,
                   "factory": pypyOwnTestFactoryOSX32,
                   "category": 'mac32'
                  },
                  {"name" : JITMACOSX64,
                   "slavenames": ["xerxes"],
                   'builddir' : JITMACOSX64,
                   'factory' : pypyJITTranslatedTestFactoryOSX64,
                   'category' : 'mac64',
                   },
                  {"name": WIN32,
                   "slavenames": ["aurora", "SalsaSalsa"],
                   "builddir": WIN32,
                   "factory": pypyOwnTestFactoryWin,
                   "category": 'win32',
                  },
                  {"name": WIN64,
                   "slavenames": ["snakepit64"],
                   "builddir": WIN64,
                   "factory": pypyOwnTestFactoryWin,
                   "category": 'win32'
                  },
                  {"name": APPLVLWIN32,
                   "slavenames": ["aurora", "SalsaSalsa"],
                   "builddir": APPLVLWIN32,
                   "factory": pypyTranslatedAppLevelTestFactoryWin,
                   "category": "win32",
                  },
                  {"name" : JITWIN32,
                   "slavenames": ["aurora", "SalsaSalsa"],
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
                  {"name" : JITFREEBSD764,
                   "slavenames": ['headless'],
                   'builddir' : JITFREEBSD764,
                   'factory' : pypyJITTranslatedTestFactoryFreeBSD,
                   "category": 'freebsd64'
                   },
                  {"name": JITFREEBSD864,
                   "slavenames": ['ananke'],
                   'builddir' : JITFREEBSD864,
                   'factory' : pypyJITTranslatedTestFactoryFreeBSD,
                   "category": 'freebsd64'
                   },
                  {"name" : JITFREEBSD964,
                   "slavenames": ['hybridlogic'],
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
                ] + ARM.builders,

    # http://readthedocs.org/docs/buildbot/en/latest/tour.html#debugging-with-manhole
    #'manhole': manhole.PasswordManhole("tcp:1234:interface=127.0.0.1",
    #                                    "buildmaster","XndZopHM"),
    'buildbotURL': 'http://buildbot.pypy.org/',  # with a trailing '/'!
    'projectURL': 'http://pypy.org/',
    'projectName': 'PyPy'}
