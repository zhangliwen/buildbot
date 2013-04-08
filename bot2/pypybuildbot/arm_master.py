
from buildbot.scheduler import Nightly, Triggerable
from pypybuildbot.util import we_are_debugging, load

pypybuilds = load('pypybuildbot.builds')
ARMCrossLock = pypybuilds.ARMCrossLock
ARMBoardLock = pypybuilds.ARMBoardLock

# ARM own test factories
jit_translation_args = ['-Ojit']
crosstranslationargs = ['--platform=arm', '--gcrootfinder=shadowstack']
crosstranslationjitargs = ['--jit-backend=armv7']
crosstranslationjitargs_raspbian = ['--jit-backend=armv6hf']
# this one needs a larger timeout due to how it is run
pypyJitBackendOnlyOwnTestFactoryARM = pypybuilds.Own(
        cherrypick=':'.join(["jit/backend/arm",
                            "jit/backend/llsupport",
                            "jit/backend/test",  # kill this one in case it is too slow
                            ]),
        timeout=6 * 3600)
pypyJitOnlyOwnTestFactoryARM = pypybuilds.Own(cherrypick="jit", timeout=2 * 3600)
pypyOwnTestFactoryARM = pypybuilds.Own(timeout=2 * 3600)

pypyCrossTranslationFactoryARM = pypybuilds.NightlyBuild(
    translationArgs=crosstranslationargs + ['-O2'],
    platform='linux-armel',
    interpreter='pypy',
    prefix=['schroot', '-c', 'armel'],
    trigger='APPLVLLINUXARM_scheduler')

pypyJITCrossTranslationFactoryARM = pypybuilds.NightlyBuild(
    translationArgs=(crosstranslationargs
                        + jit_translation_args
                        + crosstranslationjitargs),
    platform='linux-armel',
    interpreter='pypy',
    prefix=['schroot', '-c', 'armel'],
    trigger='JITLINUXARM_scheduler')

pypyCrossTranslationFactoryRaspbianHF = pypybuilds.NightlyBuild(
    translationArgs=crosstranslationargs + ['-O2'],
    platform='linux-armhf-raspbian',
    interpreter='pypy',
    prefix=['schroot', '-c', 'raspbian'],
    trigger='APPLVLLINUXARMHF_RASPBIAN_scheduler')

pypyJITCrossTranslationFactoryRaspbianHF = pypybuilds.NightlyBuild(
    translationArgs=(crosstranslationargs
                        + jit_translation_args
                        + crosstranslationjitargs_raspbian),
    platform='linux-armhf-raspbian',
    interpreter='pypy',
    prefix=['schroot', '-c', 'raspbian'],
    trigger='JITLINUXARMHF_RASPBIAN_scheduler')

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
    translationArgs=crosstranslationargs + ['-O2'],
    lib_python=True,
    app_tests=True,
    platform='linux-armel',
)

pypyARMJITTranslatedTestFactory = pypybuilds.TranslatedTests(
    translationArgs=(crosstranslationargs
                        + jit_translation_args
                        + crosstranslationjitargs),
    lib_python=True,
    pypyjit=True,
    app_tests=True,
    platform='linux-armhf-raspbian',
    )
pypyARMTranslatedAppLevelTestFactory = pypybuilds.TranslatedTests(
    translationArgs=crosstranslationargs + ['-O2'],
    lib_python=True,
    app_tests=True,
    platform='linux-armhf-raspbian',
)
#
APPLVLLINUXARM = "pypy-c-app-level-linux-armel"
APPLVLLINUXARMHF_RASPBIAN = "pypy-c-app-level-linux-armhf-raspbian"

JITLINUXARM = "pypy-c-jit-linux-armel"
JITLINUXARMHF_RASPBIAN = "pypy-c-jit-linux-armhf-raspbian"

JITBACKENDONLYLINUXARMEL = "jitbackendonly-own-linux-armel"
JITBACKENDONLYLINUXARMHF = "jitbackendonly-own-linux-armhf"

# build only
BUILDLINUXARM = "build-pypy-c-linux-armel"
BUILDJITLINUXARM = "build-pypy-c-jit-linux-armel"
BUILDLINUXARMHF_RASPBIAN = "build-pypy-c-linux-armhf-raspbian"
BUILDJITLINUXARMHF_RASPBIAN = "build-pypy-c-jit-linux-armhf-raspbian"


schedulers = [
    Nightly("nighly-arm-0-00", [
        BUILDLINUXARM,                 # on hhu-cross-armel, uses 1 core
        BUILDJITLINUXARM,              # on hhu-cross-armel, uses 1 core
        BUILDLINUXARMHF_RASPBIAN,      # on hhu-cross-raspbianhf, uses 1 core
        BUILDJITLINUXARMHF_RASPBIAN,   # on hhu-cross-raspbianhf, uses 1 core
        JITBACKENDONLYLINUXARMEL,      # on hhu-imx.53
        JITBACKENDONLYLINUXARMHF,      # on hhu-raspberry-pi
        ], branch=None, hour=0, minute=0),

    Triggerable("APPLVLLINUXARM_scheduler", [
        APPLVLLINUXARM,            # triggered by BUILDLINUXARM, on hhu-beagleboard
    ]),

    Triggerable("JITLINUXARM_scheduler", [
        JITLINUXARM,               # triggered by BUILDJITLINUXARM, on hhu-beagleboard
    ]),
    Triggerable("APPLVLLINUXARMHF_RASPBIAN_scheduler", [
        APPLVLLINUXARMHF_RASPBIAN, # triggered by BUILDLINUXARMHF_RASPBIAN, on hhu-raspberry-pi
    ]),

    Triggerable("JITLINUXARMHF_RASPBIAN_scheduler", [
        JITLINUXARMHF_RASPBIAN,    # triggered by BUILDJITLINUXARMHF_RASPBIAN, on hhu-raspberry-pi
    ]),
]

builders = [
  # ARM
  # armel
  {"name": JITBACKENDONLYLINUXARMEL,
   "slavenames": ['hhu-i.mx53'],
   "builddir": JITBACKENDONLYLINUXARMEL,
   "factory": pypyJitBackendOnlyOwnTestFactoryARM,
   "category": 'linux-armel',
   "locks": [ARMBoardLock.access('counting')],
   },
  # armhf
  {"name": JITBACKENDONLYLINUXARMHF,
   "slavenames": ['hhu-raspberry-pi'],
   "builddir": JITBACKENDONLYLINUXARMHF,
   "factory": pypyJitBackendOnlyOwnTestFactoryARM,
   "category": 'linux-armhf',
   "locks": [ARMBoardLock.access('counting')],
   },
  # app level builders
  {"name": APPLVLLINUXARM,
   "slavenames": ["hhu-beagleboard"],
   "builddir": APPLVLLINUXARM,
   "factory": pypyARMTranslatedAppLevelTestFactory,
   "category": "linux-armel",
   "locks": [ARMBoardLock.access('counting')],
   },
  {"name": JITLINUXARM,
   "slavenames": ["hhu-beagleboard"],
   'builddir': JITLINUXARM,
   'factory': pypyARMJITTranslatedTestFactory,
   'category': 'linux-armel',
   "locks": [ARMBoardLock.access('counting')],
   },
  {"name": APPLVLLINUXARMHF_RASPBIAN,
   "slavenames": ["hhu-raspberry-pi"],
   "builddir": APPLVLLINUXARMHF_RASPBIAN,
   "factory": pypyARMTranslatedAppLevelTestFactory,
   "category": "linux-armhf",
   "locks": [ARMBoardLock.access('counting')],
   },
  {"name": JITLINUXARMHF_RASPBIAN,
   "slavenames": ["hhu-raspberry-pi"],
   'builddir': JITLINUXARMHF_RASPBIAN,
   'factory': pypyARMJITTranslatedTestFactory,
   'category': 'linux-armhf',
   "locks": [ARMBoardLock.access('counting')],
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
  {"name": BUILDLINUXARMHF_RASPBIAN,
   "slavenames": ['hhu-cross-raspbianhf'],
   "builddir": BUILDLINUXARMHF_RASPBIAN,
   "factory": pypyCrossTranslationFactoryRaspbianHF ,
   "category": 'linux-armhf',
   "locks": [ARMCrossLock.access('counting')],
   },
  {"name": BUILDJITLINUXARMHF_RASPBIAN,
   "slavenames": ['hhu-cross-raspbianhf'],
   "builddir": BUILDJITLINUXARMHF_RASPBIAN,
   "factory": pypyJITCrossTranslationFactoryRaspbianHF,
   "category": 'linux-armhf',
   "locks": [ARMCrossLock.access('counting')],
  },
]
