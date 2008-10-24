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

status = WebStatus(httpPortNumber, allowForce=True)

# pypy test summary page
summary = load('pypybuildbot.summary')
status.putChild('summary', summary.Summary())


pypybuilds = load('pypybuildbot.builds')

pypyOwnTestFactory = pypybuilds.PyPyOwnTestFactory()
pypyOwnTestFactoryWin = pypybuilds.PyPyOwnTestFactory(platform="win32")

pypyTranslatedLibPythonTestFactory = pypybuilds.PyPyTranslatedLibPythonTestFactory()
pypyTranslatedLibPythonTestFactoryWin = pypybuilds.PyPyTranslatedLibPythonTestFactory(platform="win32")
pypyTranslatedLibPythonMaemoTestFactory = pypybuilds.PyPyTranslatedScratchboxTestFactory()


LINUX32 = "own-linux-x86-32"
CPYLINUX32 = "pypy-c-lib-python-linux-x86-32"
CPYWIN32 = "pypy-c-lib-python-win-32"
CPYLINUX32_VM = 'pypy-c-lib-python-linux-x86-32vm'
CPYMAEMO = "pypy-c-lib-python-maemo"

BuildmasterConfig = {
    'slavePortnum': slavePortnum,

    'change_source': [],
    'schedulers': [
    	Nightly("nightly", [LINUX32, CPYLINUX32], hour=4, minute=45),
    ],   
    'status': [status],

    'slaves': [BuildSlave(name, password)
               for (name, password)
               in passwords.iteritems()],

    'builders': [
                  {"name": LINUX32,
                   "slavenames": ["wyvern"],
                   "builddir": LINUX32,
                   "factory": pypyOwnTestFactory
                  },
                  {"name": CPYLINUX32,
                   "slavenames": ["wyvern", "cobra"],
                   "builddir": CPYLINUX32,
                   "factory": pypyTranslatedLibPythonTestFactory
                  },
                  {"name" : CPYLINUX32_VM,
                   "slavenames": ['bigdogvm1'],
                   "builddir": CPYLINUX32_VM,
                   "factory": pypyTranslatedLibPythonTestFactory
                   },
                  {"name": CPYWIN32,
                   "slavenames": ["winxp32-py2.5"],
                   "builddir": CPYWIN32,
                   "factory": pypyTranslatedLibPythonTestFactoryWin
                  },
                  {"name" : CPYMAEMO,
                   "slavenames": ['bigdogvm1'],
                   "builddir" : CPYMAEMO,
                   "factory": pypyTranslatedLibPythonMaemoTestFactory,
                   },
                ],

    'buildbotURL': 'http://codespeak.net:%d/'%(httpPortNumber),
    'projectURL': 'http://codespeak.net/pypy/',
    'projectName': 'PyPy'}

