# -*- mode: python -*-
from twisted.application import service
from buildbot.slave.bot import BuildSlave

# ---------------------------------------------------------------
# manual editing of the automatically generated buildbot.tac
#
import os.path
thisfile = os.path.join(os.getcwd(), __file__)
basedir = os.path.abspath(os.path.dirname(thisfile))
#
# ---------------------------------------------------------------

def find_passwd(slavename):
  masterdir = os.path.join(basedir, '..', 'master')
  slaveinfo = os.path.join(masterdir, 'slaveinfo.py')
  d = {}
  try:
    execfile(slaveinfo, d)
    return d['passwords'][slavename]
  except Exception, e:
    print 'error when executing ../master/slaveinfo.py: %s' % repr(e)
    print 'using default password for the slave'
    return 'default_password'
  

buildmaster_host = 'localhost'
port = 10407
slavename = 'localhost'
passwd = find_passwd(slavename)
keepalive = 600
usepty = 0
umask = None
maxdelay = 300
rotateLength = 1000000
maxRotatedFiles = None

application = service.Application('buildslave')
try:
  from twisted.python.logfile import LogFile
  from twisted.python.log import ILogObserver, FileLogObserver
  logfile = LogFile.fromFullPath("twistd.log", rotateLength=rotateLength,
                                 maxRotatedFiles=maxRotatedFiles)
  application.setComponent(ILogObserver, FileLogObserver(logfile).emit)
except ImportError:
  # probably not yet twisted 8.2.0 and beyond, can't set log yet
  pass
s = BuildSlave(buildmaster_host, port, slavename, passwd, basedir,
               keepalive, usepty, umask=umask, maxdelay=maxdelay)
s.setServiceParent(application)

