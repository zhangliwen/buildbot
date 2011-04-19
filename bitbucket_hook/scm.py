import sys
from subprocess import Popen, PIPE

def _hgexe(argv):
    proc = Popen(['hg'] + list(argv), stdout=PIPE, stderr=PIPE)
    stdout, stderr = proc.communicate()
    ret = proc.wait()
    return stdout, stderr, ret

def hg(*argv):
    argv = map(str, argv)
    stdout, stderr, ret = _hgexe(argv)
    if ret != 0:
        print >> sys.stderr, 'error: hg', ' '.join(argv)
        print >> sys.stderr, stderr
        raise Exception('error when executing hg')
    return unicode(stdout, encoding='utf-8', errors='replace')
