# -*- mode: python -*-
from twisted.application import service
from buildbot.master import BuildMaster

# ---------------------------------------------------------------
# manual editing of the automatically generated buildbot.tac
#
import os.path
thisfile = os.path.join(os.getcwd(), __file__)
basedir = os.path.abspath(os.path.dirname(thisfile))
#
# ---------------------------------------------------------------

configfile = r'master.cfg'
rotateLength = 1024*1024
maxRotatedFiles = 100

application = service.Application('buildmaster')
try:
  from twisted.python.logfile import LogFile
  from twisted.python.log import ILogObserver, FileLogObserver
  logfile = LogFile.fromFullPath("twistd.log", rotateLength=rotateLength,
                                 maxRotatedFiles=maxRotatedFiles)
  application.setComponent(ILogObserver, FileLogObserver(logfile).emit)
except ImportError:
  # probably not yet twisted 8.2.0 and beyond, can't set log yet
  pass
BuildMaster(basedir, configfile).setServiceParent(application)

