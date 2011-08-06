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
if StatusResourceBuild.__init__.__name__ == '__init__':
    StatusResourceBuild.__init__ = my_init
# Disabled.

# Disable pinging, as it seems to deadlock the client
from buildbot.status.web.builder import StatusResourceBuilder
def my_ping(self, req):
    raise Exception("pinging is disabled, as it seems to deadlock clients")
if StatusResourceBuilder.ping.__name__ == 'ping':
    StatusResourceBuilder.ping = my_ping
# Disabled.

# Forbid "force build" with empty user name
def my_force(self, req):
    name = req.args.get("username", [""])[0]
    assert name, "Please write your name in the corresponding field."
    return _previous_force(self, req)
_previous_force = StatusResourceBuilder.force
if _previous_force.__name__ == 'force':
    StatusResourceBuilder.force = my_force
# Done

# Add a link from the builder page to the summary page
def my_body(self, req):
    data = _previous_body(self, req)
    MARKER = 'waterfall</a>)'
    i = data.find(MARKER)
    if i >= 0:
        from twisted.web import html
        i += len(MARKER)
        b = self.builder_status
        url = self.path_to_root(req)+"summary?builder="+html.escape(b.getName())
        data = '%s&nbsp;&nbsp;&nbsp;(<a href="%s">view in summary</a>)%s' % (
            data[:i],
            url,
            data[i:])
    return data

_previous_body = StatusResourceBuilder.body
if _previous_body.__name__ == 'body':
    StatusResourceBuilder.body = my_body
# Done

# Add a similar link from the build page to the summary page
def my_body_2(self, req):
    data = _previous_body_2(self, req)
    MARKER1 = '<h2>Results'
    MARKER2 = '<h2>SourceStamp'
    i1 = data.find(MARKER1)
    i2 = data.find(MARKER2)
    if i1 >= 0 and i2 >= 0:
        from twisted.web import html
        b = self.build_status
        ss = b.getSourceStamp()
        branch = ss.branch or '<trunk>'
        builder_name = b.getBuilder().getName()
        url = (self.path_to_root(req) +
               "summary?builder=" + html.escape(builder_name) +
               "&branch=" + html.escape(branch))
        data = '%s&nbsp;&nbsp;&nbsp;(<a href="%s">view in summary</a>)\n\n%s'% (
            data[:i2],
            url,
            data[i2:])
    return data
_previous_body_2 = StatusResourceBuild.body
if _previous_body_2.__name__ == 'body':
    StatusResourceBuild.body = my_body_2

# Picking a random slave is not really what we want;
# let's pick the first available one instead.
Builder.CHOOSE_SLAVES_RANDOMLY = False


status = WebStatus(httpPortNumber, allowForce=True)

# pypy test summary page
summary = load('pypybuildbot.summary')
status.putChild('summary', summary.Summary(categories=['linux',
                                                       'mac',
                                                       'win',
                                                       'freebsd']))
status.putChild('nightly', PyPyList(os.path.expanduser('~/nightly'),
                                    defaultType='application/octet-stream'))


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

pypyStacklessTranslatedAppLevelTestFactory = pypybuilds.Translated(
    translationArgs=["-O2", "--stackless"], targetArgs=[],
    lib_python=False,
    app_tests = ["pypy/pytest-A-stackless.cfg"]
)

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

pypy_OjitTranslatedTestFactory = pypybuilds.Translated(
    translationArgs=['-Ojit', '--gc=hybrid', '--no-translation-jit',
                     '--gcrootfinder=asmgcc'],
    lib_python=True,
    app_tests=True
    )

pypyJITBenchmarkFactory = pypybuilds.JITBenchmark()
pypyJITBenchmarkFactory64 = pypybuilds.JITBenchmark(platform='linux64',
                                                    postfix='-64')

LINUX32 = "own-linux-x86-32"
LINUX64 = "own-linux-x86-64"
MACOSX32 =  "own-macosx-x86-32"
WIN32 = "own-win-x86-32"
APPLVLLINUX32 = "pypy-c-app-level-linux-x86-32"
APPLVLLINUX64 = "pypy-c-app-level-linux-x86-64"
STACKLESSAPPLVLLINUX32 = "pypy-c-stackless-app-level-linux-x86-32"

APPLVLWIN32 = "pypy-c-app-level-win-x86-32"
STACKLESSAPPLVLFREEBSD64 = 'pypy-c-stackless-app-level-freebsd-7-x86-64'

JITLINUX32 = "pypy-c-jit-linux-x86-32"
JITLINUX64 = "pypy-c-jit-linux-x86-64"
OJITLINUX32 = "pypy-c-Ojit-no-jit-linux-x86-32"
JITMACOSX64 = "pypy-c-jit-macosx-x86-64"
JITWIN32 = "pypy-c-jit-win-x86-32"

JITONLYLINUX32 = "jitonly-own-linux-x86-32"
JITBENCH = "jit-benchmark-linux-x86-32"
JITBENCH64 = "jit-benchmark-linux-x86-64"

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
            MACOSX32,                  # on minime
            ], hour=0, minute=0),
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
            STACKLESSAPPLVLLINUX32,    # on tannit32, uses 1 core
            #
            JITWIN32,                  # on bigboard
            STACKLESSAPPLVLFREEBSD64,  # on headless
            JITMACOSX64,               # on mvt's machine
            ], hour=3, minute=0)
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
                   "category": 'linux32',
                   # this build needs 4 CPUs
                   "locks": [TannitCPU.access('counting'),
                             TannitCPU.access('counting'),
                             TannitCPU.access('counting'),
                             TannitCPU.access('counting'),
                             ],
                  },
                  {"name": LINUX64,
                   "slavenames": ["tannit64"],
                   "builddir": LINUX64,
                   "factory": pypyOwnTestFactory,
                   "category": 'linux64',
                   # this build needs 4 CPUs
                   "locks": [TannitCPU.access('counting'),
                             TannitCPU.access('counting'),
                             TannitCPU.access('counting'),
                             TannitCPU.access('counting'),
                             ],
                  },
                  {"name": MACOSX32,
                   "slavenames": ["minime"],
                   "builddir": MACOSX32,
                   "factory": pypyOwnTestFactory,
                   "category": 'mac32'
                  },
                  {"name": WIN32,
                   "slavenames": ["bigboard"],
                   "builddir": WIN32,
                   "factory": pypyOwnTestFactoryWin,
                   "category": 'win32'
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
                  {"name": STACKLESSAPPLVLLINUX32,
                   "slavenames": ["bigdogvm1", "tannit32"],
                   "builddir": STACKLESSAPPLVLLINUX32,
                   "factory": pypyStacklessTranslatedAppLevelTestFactory,
                   "category": 'linux32-stackless',
                   "locks": [TannitCPU.access('counting')],
                  },
                  {"name": OJITLINUX32,
                   "slavenames": ["bigdogvm1", "tannit32"],
                   "builddir": OJITLINUX32,
                   "factory": pypy_OjitTranslatedTestFactory,
                   "category": 'linux32',
                   "locks": [TannitCPU.access('counting')],
                  },
                  {"name": APPLVLWIN32,
                   "slavenames": ["bigboard"],
                   "builddir": APPLVLWIN32,
                   "factory": pypyTranslatedAppLevelTestFactoryWin,
                   "category": "win32"
                  },
                  {"name" : STACKLESSAPPLVLFREEBSD64,
                   "slavenames": ['headless'],
                   'builddir' : STACKLESSAPPLVLFREEBSD64,
                   'factory' : pypyStacklessTranslatedAppLevelTestFactory,
                   "category": 'freebsd64-stackless'
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
                  {"name" : JITMACOSX64,
                   "slavenames": ["macmini-mvt", "xerxes"],
                   'builddir' : JITMACOSX64,
                   'factory' : pypyJITTranslatedTestFactoryOSX64,
                   'category' : 'mac64',
                   },
                  {"name" : JITWIN32,
                   "slavenames": ["bigboard"],
                   'builddir' : JITWIN32,
                   'factory' : pypyJITTranslatedTestFactoryWin,
                   'category' : 'win32',
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
                   "factory": pypyJITBenchmarkFactory,
                   "category": 'benchmark-run',
                   # the locks are acquired with fine grain inside the build
                  },
                  {"name": JITBENCH64,
                   "slavenames": ["tannit64"],
                   "builddir": JITBENCH64,
                   "factory": pypyJITBenchmarkFactory64,
                   "category": "benchmark-run",
                   # the locks are acquired with fine grain inside the build
                   },
                ],

    'buildbotURL': 'http://buildbot.pypy.org/',  # with a trailing '/'!
    'projectURL': 'http://pypy.org/',
    'projectName': 'PyPy'}
