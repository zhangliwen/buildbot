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

pypyTranslatedLibPythonTestFactory = pypybuilds.PyPyTranslaledLibPythonTestFactory()

BuildmasterConfig = {
    'slavePortnum': slavePortnum,

    'change_source': [],
    'schedulers': [
    	Nightly("nightly", ["own-linux-x86-32", "pypy-c-lib-python-linux-x86-32"], hour=4, minute=45),
    ],   
    'status': [status],

    'slaves': [BuildSlave(name, password)
               for (name, password)
               in passwords.iteritems()],

    'builders': [
                  {"name": "own-linux-x86-32",
                   "slavenames": ["wyvern", "cobra"],
                   "builddir": "own-linux-x86-32",
                   "factory": pypyOwnTestFactory
                  },
                  {"name": "pypy-c-lib-python-linux-x86-32",
                   "slavenames": ["wyvern", "cobra"],
                   "builddir": "pypy-c-lib-python-linux-x86-32",
                   "factory": pypyTranslatedLibPythonTestFactory
                  },
                  
                ],

    'buildbotURL': 'http://codespeak.net:%d/'%(httpPortNumber),
    'projectURL': 'http://codespeak.net/pypy/',
    'projectName': 'PyPy'}

