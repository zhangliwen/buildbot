from buildbot.scheduler import Nightly
from buildbot.buildslave import BuildSlave
from buildbot.status.html import WebStatus

from buildbot.process import factory
from buildbot.steps import source, shell


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

pypyOwnFactory = factory.BuildFactory()
pypyOwnFactory.addStep(source.SVN("https://codespeak.net/svn/pypy/branch/pypy-pytrunk"))
pypyOwnFactory.addStep(shell.ShellCommand(
    description="pytest",
    command="py/bin/py.test pypy/module/__builtin__ pypy/module/operator --session=FileLogSession --filelog=pytest.log".split(),
    logfiles={'pytestLog': 'pytest.log'}))

BuildmasterConfig = {
    'slavePortnum': slavePortnum,

    'change_source': [],
    'schedulers': [Nightly("nightly",
                           ["pypy-own-linux", "pypy-own-other-linux"], hour=19)],
    'status': [status],

    'slaves': [BuildSlave(name, password)
               for (name, password)
               in passwords.iteritems()],

    'builders': [
                  {"name": "pypy-own-linux",
                   "slavenames": ["vitaly"],
                   "builddir": "pypy-own-linux",
                   "factory": pypyOwnFactory
                  },
                  {"name": "pypy-own-other-linux",
                   "slavenames": ["fido"],
                   "builddir": "pypy-own-other-linux",
                   "factory": pypyOwnFactory
                  }
                ],

    'buildbotURL': 'http://localhost:%d/' % (httpPortNumber,),
    'projectURL': 'http://codespeak.net/pypy/',
    'projectName': 'PyPy'}

import pypybuildbot.summary
reload(pypybuildbot.summary)
summary = pypybuildbot.summary

# pypy test summary page
status.putChild('summary', summary.Summary())
