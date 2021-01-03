
import os
from buildbot.scheduler import Nightly, Triggerable
from buildbot.schedulers.forcesched import (ForceScheduler, ValidationError,
         CodebaseParameter, StringParameter, BaseParameter, UserNameParameter)
from buildbot.buildslave import BuildSlave
from buildbot.buildslave.base import log
from buildbot.status.html import WebStatus
from buildbot.status.web import authz
from buildbot.process.build import Build
#from buildbot import manhole
from pypybuildbot.pypylist import PyPyList, NumpyStatusList, ReleaseList
from pypybuildbot.ircbot import IRC  # side effects
from pypybuildbot.util import we_are_debugging, isRPython
from buildbot.changes import filter
from buildbot.changes.hgpoller import HgPoller
from twisted.web.static import File

# Forbid "force build" with empty user name
class CustomForceScheduler(ForceScheduler):
    def __init__(self, *args, **kwargs):
        ForceScheduler.__init__(self, *args, properties=[], **kwargs)

    def force(self, owner, builder_name, **kwargs):
        if not owner:
            raise ValidationError("Please write your name in the corresponding field.")
        return ForceScheduler.force(self, owner, builder_name, **kwargs)


class BenchmarkForceScheduler(CustomForceScheduler):
    '''
    A ForceScheduler with an extra field: benchmark_branch
    '''
    def __init__(self, name, builderNames,
            benchmark_branch=StringParameter(name="benchmark_branch",
                                             label="Benchmark repo branch:",
                                             default="default", length=20),
            properties=[ CodebaseParameter('PyPy repo', label='PyPy Repo')],
            **kwargs):
        CustomForceScheduler.__init__(self, name, builderNames, **kwargs)
        if self.checkIfType(benchmark_branch, BaseParameter):
            self.benchmark_branch = benchmark_branch
        else:
            config.error("ForceScheduler benchmark_branch must be a StringParameter: %r" %
                         pypy_branch)
        self.all_fields.append(benchmark_branch)
        self.forcedProperties.append(benchmark_branch)

    def force(self, owner, builderNames=None, **kwargs):
        CustomForceScheduler.force(self, owner, builderNames, **kwargs)

# Forbid "stop build" without a reason that starts with "!"
def _checkStopBuild(self, reason=""):
    if ": !" not in reason:
        raise ValidationError("Please write a reason that starts with '!'.")
    return _baseStopBuild(self, reason)
_baseStopBuild = Build.stopBuild
Build.stopBuild = _checkStopBuild


if we_are_debugging():
    channel = '#buildbot-test'
else:
    channel = '#pypy'

authz_cfg = authz.Authz(pingBuilder=False, forceBuild=True, forceAllBuilds=True,
                        stopBuild=True, stopAllBuilds=True,
                        cancelPendingBuild=True, pauseSlave=True)
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
status.putChild('benchmark-results', File(os.path.expanduser('~/bench_results')))
status.putChild('pypy', ReleaseList(os.path.expanduser('~/public_html/mirror')))


pypybuilds = load('pypybuildbot.builds')

# all ARM buildbot configuration is in arm_master.py
# ARM = load('pypybuildbot.arm_master')

BenchmarkerLock = pypybuilds.BenchmarkerLock
WinSlaveLock = pypybuilds.WinSlaveLock
#SpeedOldLock = pypybuilds.SpeedOldLock
Bencher4Lock = pypybuilds.Bencher4Lock
AARCH64Lock = pypybuilds.AARCH64Lock

pypyOwnTestFactory = pypybuilds.Own()
pypyOwnTestFactoryWin = pypybuilds.Own(platform="win32")
pypyOwnTestFactoryWin64 = pypybuilds.Own(platform="win64")
pypyJitOnlyOwnTestFactory = pypybuilds.Own(cherrypick="jit")

# OSX 32bit tests require a larger timeout to finish
pypyOwnTestFactoryOSX32 = pypybuilds.Own(timeout=3*3600) # XXX Own or RPython?

pypyRPythonTestFactory = pypybuilds.RPython()
pypyRPythonTestFactoryWin = pypybuilds.RPython(platform="win32")
pypyRPythonTestFactoryWin64 = pypybuilds.RPython(platform="win64")
pypyRPythonTestFactoryAarch64 = pypybuilds.RPython(timeout=3*3600)
pypyJitOnlyRPythonTestFactory = pypybuilds.RPython(cherrypick="jit")

# OSX 32bit tests require a larger timeout to finish
pypyRPythonTestFactoryOSX32 = pypybuilds.RPython(timeout=3*3600) # XXX Own or RPython?

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

pypyJITTranslatedTestFactoryWin64 = pypybuilds.Translated(
    platform="win64",
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

pypyJITTranslatedTestFactoryAARCH64 = pypybuilds.Translated(
    platform='aarch64',
    translationArgs=jit_translation_args,
    targetArgs=[],
    lib_python=True,
    pypyjit=True,
    app_tests=True)

pypyJITBenchmarkFactory = pypybuilds.JITBenchmark(host='benchmarker')
pypyJITBenchmarkFactory64 = pypybuilds.JITBenchmark(platform='linux64',
                                                           host='benchmarker',
                                                           postfix='-64')
pypyJITBenchmarkFactory64_speed = pypybuilds.JITBenchmarkSingleRun(
    platform='linux64',
    host='speed_python',
    postfix='-64')

pypyNumpyCompatability = pypybuilds.NativeNumpyTests(platform='linux64')
pypyNumpyCompatabilityWin = pypybuilds.NativeNumpyTests(platform='win32')

#

LINUX32OWN = "own-linux-x86-32"
LINUX64OWN = "own-linux-x86-64"
AARCH64OWN = "own-linux-aarch64"
LINUX_S390XOWN = "own-linux-s390x"
MACOSX32OWN = "own-macosx-x86-32"
WIN32OWN = "own-win-x86-32"
WIN64OWN = "own-win-x86-64"

LINUX32RPYTHON = "rpython-linux-x86-32"
LINUX64RPYTHON = "rpython-linux-x86-64"
AARCH64RPYTHON = "rpython-linux-aarch64"
LINUX_S390XRPYTHON = "rpython-linux-s390x"
MACOSX32RPYTHON = "rpython-macosx-x86-32"
WIN32RPYTHON = "rpython-win-x86-32"
WIN64RPYTHON = "rpython-win-x86-64"

APPLVLLINUX32 = "pypy-c-app-level-linux-x86-32"
APPLVLLINUX64 = "pypy-c-app-level-linux-x86-64"
APPLVLWIN32 = "pypy-c-app-level-win-x86-32"

LIBPYTHON_LINUX32 = "pypy-c-lib-python-linux-x86-32"
LIBPYTHON_LINUX64 = "pypy-c-lib-python-linux-x86-64"

JITLINUX32 = "pypy-c-jit-linux-x86-32"
JITLINUX64 = "pypy-c-jit-linux-x86-64"
JITAARCH64 = "pypy-c-jit-linux-aarch64"
JITLINUX_S390X = 'pypy-c-jit-linux-s390x'
JITMACOSX64 = "pypy-c-jit-macosx-x86-64"
#JITMACOSX64_2 = "pypy-c-jit-macosx-x86-64-2"
JITWIN32 = "pypy-c-jit-win-x86-32"

JITONLYLINUXPPC64 = "jitonly-own-linux-ppc-64"
JITBENCH64 = "jit-benchmark-linux-x86-64"
CPYTHON_64 = "cpython-2-benchmark-x86-64"
NUMPY_64 = "numpy-compatibility-linux-x86-64"
NUMPY_WIN = "numpy-compatibility-win-x86-32"

# buildbot builder
PYPYBUILDBOT = 'pypy-buildbot'
JITFREEBSD964 = 'pypy-c-jit-freebsd-9-x86-64'

JITWIN64 = "pypy-c-jit-win-x86-64"
JITFREEBSD764 = 'pypy-c-jit-freebsd-7-x86-64'
JITFREEBSD864 = 'pypy-c-jit-freebsd-8-x86-64'
JITBENCH64_NEW = 'jit-benchmark-linux-x86-64-single-run'
inactive_slaves = [
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
                  {"name" : JITFREEBSD964,
                   "slavenames": ['hybridlogic', 'tavendo-freebsd-9.2-amd64'],
                   'builddir' : JITFREEBSD964,
                   'factory' : pypyJITTranslatedTestFactoryFreeBSD,
                   "category": 'freebsd64'
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

    'change_source': [
        # For now, you should list here the branches on which the various Nightly run.
        # This should be fixed more properly in the next revision of heptapod.
        # These HgPollers are used to get the revision at the head in these branches
        # and then the nightly schedulers use them.  We see them in the build pages
        # in the "Revision" property.  Any build with such a "Revision" property will
        # use exactly that revision (at least in our nightly builds).
        # NOTE obscure hack: we can't give the exact same URL to both, so we use
        # small variants
        HgPoller('https://foss.heptapod.net/pypy/pypy/', workdir='hgpoller-workdir',
                 branch='default', pollinterval=20*60),
        HgPoller('https://foss.heptapod.net/pypy/pypy', workdir='hgpoller-workdir',
                 branch='py3.7', pollinterval=20*60+17),
        ],

    'schedulers': [
        # the benchmarks run on benchmarker
        # 64 bit linux tests run on bencher4.soft-dev.org.
        # 32 bit linux tests run on benchmarker.
        # windows tests run on SalsaSalsa
        Nightly("nightly-0-00", [
            # linux tests
            LINUX32OWN,                # on benchmarker4_32, uses all cores
            LINUX64OWN,                # on bencher4, uses all cores
            AARCH64OWN,
            WIN64OWN,                  # on SalsaSalsa
            LINUX_S390XOWN,
            JITLINUX32,                # on benchmarker4_32, uses 1 core
            JITLINUX64,                # on bencher4, uses 1 core
            JITAARCH64,
            JITLINUX_S390X,
            #APPLVLLINUX32,
            #APPLVLLINUX64,             # on bencher4, uses 1 core
            # other platforms
            #MACOSX32,                 # on minime
            JITWIN64,                  # on SalsaSalsa
            #JITFREEBSD764,
            #JITFREEBSD864,
            #JITFREEBSD964,
            JITMACOSX64,               # on xerxes
            # buildbot selftest
            #PYPYBUILDBOT,
            ], branch='default', hour=0, minute=0,
            onlyIfChanged=True,
        ),

        Nightly("nightly-0-01", [
            LINUX32RPYTHON,            # on benchermarker_32, uses all cores
            LINUX64RPYTHON,            # on bencher4, uses all cores
            AARCH64RPYTHON,
            WIN64RPYTHON,              # on SalsaSalsa
            LINUX_S390XRPYTHON,
            ], branch='default', hour=1, minute=0, onlyIfChanged=True,
            fileIsImportant=isRPython,
            change_filter=filter.ChangeFilter(branch='default'),
        ),

        Nightly("nightly-1-00", [
            JITBENCH64,                # on benchmarker, uses 1 core (in part exclusively)
            #JITBENCH64_NEW,            # on speed64, uses 1 core (in part exclusively)

            ], branch='default', hour=7, minute=0,
            onlyIfChanged=True,
        ),

        Nightly("nightly-1-01", [
            JITBENCH64,                # on benchmarker, uses 1 core (in part exclusively)
            #JITBENCH64_NEW,            # on speed64, uses 1 core (in part exclusively)

            ], branch='py3.7', hour=11, minute=0,
            onlyIfChanged=True,
        ),

        Triggerable("NUMPY64_scheduler", [
            #NUMPY_64,                  # uses 1 core, takes about 5min.
        ]),

        Triggerable("NUMPYWIN_scheduler", [
            #NUMPY_WIN,                  # on SalsaSalsa
        ]),

        #Nightly("nightly-3-01-py3.5", [LINUX64, JITLINUX64,],
        #        branch="py3.5", hour=3, minute=0),

        Nightly("nightly-3-00-py3.7", [
            LINUX32OWN,                # on bencher4_32, uses all cores
            JITLINUX32,                # on bencher4_32, uses 1 core
            LINUX64OWN,                # on bencher4, uses all cores
            AARCH64OWN,
            JITLINUX64,                # on bencher4, uses 1 core
            JITAARCH64,
            JITMACOSX64,               # on xerxes
            WIN64OWN,                  # on SalsaSalsa
            JITWIN64,                  # on SalsaSalsa
            ], branch="py3.7", hour=3, minute=0,
            onlyIfChanged=True # uses the second HgPoller?
        ),

        # this one has faithfully run every night even though the latest
        # change to that branch was in January 2013.  Re-enable one day.
        #Nightly("nighly-ppc", [
        #    JITONLYLINUXPPC64,         # on gcc1
        #    ], branch='ppc-jit-backend', hour=1, minute=0),
        BenchmarkForceScheduler('Force Build ',
            builderNames=[
                        JITBENCH64,
                        JITBENCH64_NEW,
                    ], properties=[]),
        CustomForceScheduler('Force Build',
            builderNames=[
                        PYPYBUILDBOT,
                        LINUX32OWN,
                        LINUX64OWN,
                        AARCH64OWN,
                        MACOSX32OWN,
                        WIN32OWN,
                        LINUX32RPYTHON,
                        LINUX64RPYTHON,
                        AARCH64RPYTHON,
                        MACOSX32RPYTHON,
                        WIN32RPYTHON,
                        WIN64RPYTHON,

                        APPLVLLINUX32,
                        APPLVLLINUX64,
                        APPLVLWIN32,

                        LIBPYTHON_LINUX32,
                        LIBPYTHON_LINUX64,

                        JITLINUX32,
                        JITLINUX64,
                        JITAARCH64,
                        JITMACOSX64,
                        JITWIN32,
                        #JITFREEBSD964,

                        JITONLYLINUXPPC64,
                        NUMPY_64,
                        NUMPY_WIN,
                        WIN64OWN,
                        #JITMACOSX64_2,
                        JITWIN64,
                        #JITFREEBSD764,
                        #JITFREEBSD864,

                        LINUX_S390XOWN,
                        LINUX_S390XRPYTHON,
                        JITLINUX_S390X,

            ]), #  + ARM.builderNames, properties=[]),
    ], # + ARM.schedulers,

    'status': [status, ircbot],

    'slaves': [BuildSlave(name, password, **extra_opts.get(name, {}))
               for (name, password)
               in passwords.iteritems()],

    'builders': [
                  {"name": LINUX32OWN,
                   "slavenames": ["salsa_32", "benchmarker32"],
                   "builddir": LINUX32OWN,
                   "factory": pypyOwnTestFactory,
                   "category": 'linux32',
                   "locks": [BenchmarkerLock.access('counting')],
                  },
                  {"name": LINUX32RPYTHON,
                   "slavenames": ["salsa_32", "benchmarker32"],
                   "builddir": LINUX32RPYTHON,
                   "factory": pypyRPythonTestFactory,
                   "category": 'linux32',
                   "locks": [BenchmarkerLock.access('counting')],
                  },
                  {"name": LINUX64OWN,
                   #"slavenames": ["bencher4", "speed-old"],
                   "slavenames": ["bencher4", "benchmarker64"],
                   "builddir": LINUX64OWN,
                   "factory": pypyOwnTestFactory,
                   "category": 'linux64',
                   "locks": [Bencher4Lock.access('counting')],
                  },
                  {"name": AARCH64OWN,
                   "slavenames": ["aarch64_aws"],
                   "builddir": AARCH64OWN,
                   "factory": pypyOwnTestFactory,
                   "category": 'aarch64',
                   "locks": [AARCH64Lock.access('counting')],
                  },
                  {"name": LINUX64RPYTHON,
                   #"slavenames": ["bencher4", "speed-old"],
                   "slavenames": ["bencher4", "benchmarker64"],
                   "builddir": LINUX64RPYTHON,
                   "factory": pypyRPythonTestFactory,
                   "category": 'linux64',
                   "locks": [Bencher4Lock.access('counting')],
                  },
                  {"name": AARCH64RPYTHON,
                   "slavenames": ["aarch64_aws"],
                   "builddir": AARCH64RPYTHON,
                   "factory": pypyRPythonTestFactoryAarch64,
                   "category": 'aarch64',
                   "locks": [AARCH64Lock.access('counting')],
                  },
                  {"name": APPLVLLINUX32,
                   #"slavenames": ["allegro32"],
                   "slavenames": ["benchmarker32"],
                   "builddir": APPLVLLINUX32,
                   "factory": pypyTranslatedAppLevelTestFactory,
                   'category': 'linux32',
                   "locks": [BenchmarkerLock.access('counting')],
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
                   "slavenames": ["bencher4_32"],
                   #"slavenames": ["allegro32"],
                   "builddir": LIBPYTHON_LINUX32,
                   "factory": pypyTranslatedLibPythonTestFactory,
                   'category': 'linux32',
                   "locks": [BenchmarkerLock.access('counting')],
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
                   "slavenames": ["bencher4_32", "salsa_32", "benchmarker32"],
                   'builddir' : JITLINUX32,
                   'factory' : pypyJITTranslatedTestFactory,
                   'category' : 'linux32',
                   "locks": [BenchmarkerLock.access('counting')],
                   },
                  {'name': JITLINUX64,
                   #'slavenames': ["bencher4", "speed-old"],
                   'slavenames': ["bencher4", "benchmarker64"],
                   'builddir': JITLINUX64,
                   'factory': pypyJITTranslatedTestFactory64,
                   'category': 'linux64',
                   "locks": [Bencher4Lock.access('counting')],
                  },
                  {'name': JITAARCH64,
                   #'slavenames': ["bencher4", "speed-old"],
                   'slavenames': ["aarch64_aws"],
                   'builddir': JITAARCH64,
                   'factory': pypyJITTranslatedTestFactoryAARCH64,
                   'category': 'aarch64',
                   "locks": [AARCH64Lock.access('counting')],
                  },
                  {"name": JITBENCH64,
                   "slavenames": ["benchmarker"],
                   "builddir": JITBENCH64,
                   "factory": pypyJITBenchmarkFactory64,
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
                  {"name": MACOSX32OWN,
                   "slavenames": ["minime"],
                   "builddir": MACOSX32OWN,
                   "factory": pypyOwnTestFactoryOSX32,
                   "category": 'mac32'
                  },
                  {"name": MACOSX32RPYTHON,
                   "slavenames": ["minime"],
                   "builddir": MACOSX32RPYTHON,
                   "factory": pypyRPythonTestFactoryOSX32,
                   "category": 'mac32'
                  },
                  {"name" : JITMACOSX64,
                   "slavenames": ["rebuy-de", "tosh", "osx-10.9-x64-dw", "billenstein-sierra"],  # "xerxes"
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

                  # Windows
                  {"name": WIN32OWN,
                   "slavenames": ["SalsaSalsa"],
                   "builddir": WIN32OWN,
                   "factory": pypyOwnTestFactoryWin,
                   "locks": [WinSlaveLock.access('counting')],
                   "category": 'win32',
                  },
                  {"name": WIN32RPYTHON,
                   "slavenames": ["SalsaSalsa"],
                   "builddir": WIN32RPYTHON,
                   "factory": pypyRPythonTestFactoryWin,
                   "locks": [WinSlaveLock.access('counting')],
                   "category": 'win32',
                  },
                 {"name": APPLVLWIN32,
                   "slavenames": ["SalsaSalsa", ],
                   "builddir": APPLVLWIN32,
                   "factory": pypyTranslatedAppLevelTestFactoryWin,
                   "locks": [WinSlaveLock.access('counting')],
                   "category": "win32",
                  },
                  {"name" : JITWIN32,
                   "slavenames": ["SalsaSalsa"],
                   'builddir' : JITWIN32,
                   'factory' : pypyJITTranslatedTestFactoryWin,
                   "locks": [WinSlaveLock.access('counting')],
                   'category' : 'win32',
                   },
                  {"name": WIN64OWN,
                   "slavenames": ["SalsaSalsa64"],
                   "builddir": WIN64OWN,
                   "factory": pypyOwnTestFactoryWin64,
                   "category": 'win64',
                   "locks": [WinSlaveLock.access('counting')],
                  },
                  {"name": WIN64RPYTHON,
                   "slavenames": ["SalsaSalsa64"],
                   "builddir": WIN64RPYTHON,
                   "factory": pypyOwnTestFactoryWin64,
                   "category": 'win64',
                   "locks": [WinSlaveLock.access('counting')],
                  },
                  {"name" : JITWIN64,
                   "slavenames": ["SalsaSalsa64"],
                   'builddir' : JITWIN64,
                   'factory' : pypyJITTranslatedTestFactoryWin64,
                   'category' : 'win64',
                   "locks": [WinSlaveLock.access('counting')],
                   },

                 # PPC
                  {"name": JITONLYLINUXPPC64,
                   "slavenames": ['gcc1'],
                   "builddir": JITONLYLINUXPPC64,
                   "factory": pypyJitOnlyOwnTestFactory,
                   "category": 'linux-ppc64',
                   },
                  {'name': NUMPY_64,
                   'slavenames': ["bencher4", "benchmarker64"],
                   'builddir': NUMPY_64,
                   'factory': pypyNumpyCompatability,
                   'category': 'numpy',
                   'locks': [BenchmarkerLock.access('counting')],
                   "locks": [Bencher4Lock.access('counting')],
                  },
                  {'name': NUMPY_WIN,
                   'slavenames': ["SalsaSalsa"],
                   'builddir': NUMPY_WIN,
                   'factory': pypyNumpyCompatabilityWin,
                   "locks": [WinSlaveLock.access('counting')],
                   'category': 'numpy',
                  },
                  {'name': PYPYBUILDBOT,
                   'slavenames': ['cobra'],
                   'builddir': PYPYBUILDBOT,
                   'factory': pypybuilds.PyPyBuildbotTestFactory(),
                   'category': 'buildbot',
                   "locks": [Bencher4Lock.access('counting')],
                  },
                  # S390X
                  {"name": LINUX_S390XOWN,
                   "slavenames": ["s390x-slave"],
                   "builddir": LINUX_S390XOWN,
                   "factory": pypyOwnTestFactory,
                   "category": 'linux-s390x',
                  },
                  {"name": LINUX_S390XRPYTHON,
                   "slavenames": ["s390x-slave"],
                   "builddir": LINUX_S390XRPYTHON,
                   "factory": pypyRPythonTestFactory,
                   "category": 'linux-s390x',
                  },
                  {'name': JITLINUX_S390X,
                   'slavenames': ['s390x-slave'],
                   'builddir': JITLINUX_S390X,
                   'factory': pypyJITTranslatedTestFactoryS390X,
                   'category': 'linux-s390x',
                  },
                ], # + ARM.builders,

    # http://readthedocs.org/docs/buildbot/en/latest/tour.html#debugging-with-manhole
    #'manhole': manhole.PasswordManhole("tcp:1234:interface=127.0.0.1",
    #                                    "buildmaster","XndZopHM"),
    'buildbotURL': 'http://buildbot.pypy.org/',  # with a trailing '/'!
    'projectURL': 'http://pypy.org/',
    'projectName': 'PyPy',
    'logMaxSize': 5*1024*1204, # 5M
    }
