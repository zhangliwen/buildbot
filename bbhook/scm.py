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


def get_diff(local_repo, hgid):
    out = hg('-R', local_repo, 'diff', '-b', '--git', '-c', hgid)
    out = out.splitlines(True)
    out_iter = iter(out)
    lines = []
    for line in out_iter:
        lines.append(line)
        if line == 'GIT binary patch\n':
            out_iter.next()  # discard literal line
            lines.append('\n[cut]\n')

            for item in out_iter:
                if item[0]!='z':
                    break  # binary patches end with a empty line


    return u''.join(lines)


if __name__=='__main__':
    # needs the pypy repo
    print get_diff(sys.argv[1], '426be91e82b0f91b09a028993d2364f1d62f1615').encode('utf-8')
