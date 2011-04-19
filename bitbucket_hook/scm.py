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


def get_diff(local_repo, hgid, files):
    import re
    binary = re.compile('^GIT binary patch$', re.MULTILINE)
    files = [item['file'] for item in files]
    lines = []
    for filename in files:
        out = hg('-R', local_repo, 'diff', '--git', '-c', hgid,
                      local_repo.join(filename))
        match = binary.search(out)
        if match:
            # it's a binary patch, omit the content
            out = out[:match.end()]
            out += u'\n[cut]'
        lines.append(out)
    return u'\n'.join(lines)
