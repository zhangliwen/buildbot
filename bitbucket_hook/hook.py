import socket
import sys
import py
import os.path

LOCAL_REPOS = py.path.local(__file__).dirpath('repos')
REMOTE_BASE = 'http://bitbucket.org'

if socket.gethostname() == 'viper':
    # for debugging, antocuni's settings
    SMTP_SERVER = "out.alice.it"
    SMTP_PORT = 25
    ADDRESS = 'anto.cuni@gmail.com'
    #
    CHANNEL = '#test'
    BOT = '/tmp/commit-bot/message'
else:
    # real settings, (they works on codespeak at least)
    SMTP_SERVER = 'localhost'
    SMTP_PORT = 25
    ADDRESS = 'pypy-svn@codespeak.net'
    #
    CHANNEL = '#pypy'
    BOT = '/svn/hooks/commit-bot/message'

hgexe = str(py.path.local.sysfind('hg'))

TEMPLATE = u"""\
Author: {author}
Branch: {branches}
Changeset: r{rev}:{node|short}
Date: {date|isodate}
%(url)s

Log:\t{desc|fill68|tabindent}

"""

class BitbucketHookHandler(object):

    def _hgexe(self, argv):
        from subprocess import Popen, PIPE
        proc = Popen([hgexe] + list(argv), stdout=PIPE, stderr=PIPE)
        stdout, stderr = proc.communicate()
        ret = proc.wait()
        return stdout, stderr, ret

    def hg(self, *argv):
        argv = map(str, argv)
        stdout, stderr, ret = self._hgexe(argv)
        if ret != 0:
            print >> sys.stderr, 'error: hg', ' '.join(argv)
            print >> sys.stderr, stderr
            raise Exception('error when executing hg')
        return unicode(stdout, encoding='utf-8', errors='replace')

    def send(self, from_, to, subject, body, test=False):
        import smtplib
        from email.mime.text import MIMEText
        if not test:
            smtp = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        # Is this a valid workaround for unicode errors?
        body = body.encode('ascii', 'xmlcharrefreplace')
        msg = MIMEText(body, _charset='utf-8')
        msg['From'] = from_
        msg['To'] = to
        msg['Subject'] = subject
        if test:
            print '#' * 20
            print "Email contents:\n"
            print from_
            print to
            print msg.get_payload(decode=True)
        else:
            smtp.sendmail(from_, [to], msg.as_string())

    def send_irc_message(self, message, test=False):
        import subprocess
        if test:
            print message + '\n'
        else:
            return subprocess.call([BOT, CHANNEL, message])

    def handle(self, payload, test=False):
        path = payload['repository']['absolute_url']
        self.payload = payload
        self.local_repo = LOCAL_REPOS.join(path)
        self.remote_repo = REMOTE_BASE + path
        if not self.local_repo.check(dir=True):
            print >> sys.stderr, 'Ignoring unknown repo', path
            return
        self.hg('pull', '-R', self.local_repo)
        self.handle_irc_message(test)
        self.handle_diff_email(test)

    USE_COLOR_CODES = True
    def handle_irc_message(self, test=False):
        import operator
        commits = sorted(self.payload['commits'],
                         key=operator.itemgetter('revision'))
        for commit in commits:
            author = commit['author']
            branch = commit['branch']
            node = commit['node']
            files = [f['file'] for f in commit['files']]
            common_prefix = os.path.commonprefix(files)
            pathlen = len(common_prefix) + 2
            if self.USE_COLOR_CODES:
                author = '\x0312%s\x0F' % author   # in blue
                branch = '\x02%s\x0F'   % branch   # in bold
                node = '\x0311%s\x0F'   % node     # in azure
            message = commit['message'].replace('\n', ' ')
            part1 = '%s %s %s /%s: ' % (author, branch, node, common_prefix)
            totallen = 160 + pathlen
            if len(message) + len(part1) <= totallen:
                irc_msg = part1 + message
            else:
                maxlen = totallen - (len(part1) + 3)
                irc_msg = part1 + message[:maxlen] + '...'
            if test:
                print "#" * 20
                print "IRC messages:"
            self.send_irc_message(irc_msg, test)
            if test:
                print

    def handle_diff_email(self, test=False):
        import operator
        commits = sorted(self.payload['commits'],
                         key=operator.itemgetter('revision'))
        for commit in commits:
            self.send_diff_for_commit(commit, test)

    def send_diff_for_commit(self, commit, test=False):
        hgid = commit['raw_node']
        sender = commit['author'] + ' <commits-noreply@bitbucket.org>'
        lines = commit['message'].splitlines()
        line0 = lines and lines[0] or ''
        reponame = self.payload['repository']['name']
        # TODO: maybe include the modified paths in the subject line?
        url = self.remote_repo + 'changeset/' + commit['node'] + '/'
        template = TEMPLATE % {'url': url}
        subject = '%s %s: %s' % (reponame, commit['branch'], line0)
        body = self.hg('-R', self.local_repo, 'log', '-r', hgid,
                 '--template', template)
        diff = self.get_diff(hgid, commit['files'])
        body = body+diff
        self.send(sender, ADDRESS, subject, body, test)

    def get_diff(self, hgid, files):
        import re
        binary = re.compile('^GIT binary patch$', re.MULTILINE)
        files = [item['file'] for item in files]
        lines = []
        for filename in files:
            out = self.hg('-R', self.local_repo, 'diff', '--git', '-c', hgid,
                          self.local_repo.join(filename))
            match = binary.search(out)
            if match:
                # it's a binary patch, omit the content
                out = out[:match.end()]
                out += u'\n[cut]'
            lines.append(out)
        return u'\n'.join(lines)


if __name__ == '__main__':
    import hook as hookfile
    repopath = os.path.dirname(os.path.dirname(hookfile.__file__))
    print 'Repository path:', repopath
    test_payload = {u'repository': {u'absolute_url': '',
                                    u'name': u'test',
                                    u'owner': u'antocuni',
                                    u'slug': u'test',
                                    u'website': u''},
                    u'user': u'antocuni'}

    test_payload[u'commits'] = [
                            {u'author': u'antocuni',
                            u'branch': u'default',
                            u'files': [{u'file': u'bitbucket_hook/hook.py', u'type': u'modified'},
                                      {u'file': u'bitbucket_hook/__init__.py', u'type': u'added'},
                                      {u'file': u'bitbucket_hook/test/__init__.py', u'type': u'added'},
                                      {u'file': u'bitbucket_hook/test/test_hook.py', u'type': u'added'}],
                            u'message': 'partially refactor the hook to be more testable, and write a test for the fix in 12cc0caf054d',
                            u'node': u'9c7bc068df88',
                            u'parents': [u'12cc0caf054d'],
                            u'raw_node': u'9c7bc068df8850f4102c610d2bee3cdef67b30e6',
                            u'revision': 391,
                            u'size': 753,
                            u'timestamp': u'2010-12-19 14:45:44'}]

##    # To regenerate:
##    from urllib2 import urlopen
##    url = ("https://api.bitbucket.org/1.0/repositories/pypy/buildbot/"
##           "changesets/%s/")
##    req = urlopen(url)
##    test_payload = req.read()
##    req.close()
##    test_nodes = (u'81d52c8e34ba', u'47b731b0f331')
##    commits = test_payload['commits']
##    commits = [commit for commit in commits if commit['node'] in test_nodes]
##    test_payload['commits'] = commits
    LOCAL_REPOS = py.path.local(repopath)

    hook = BitbucketHookHandler()
    hook.handle(test_payload, test=True)
