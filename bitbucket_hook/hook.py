import os.path
import py
import socket
import subprocess
import sys
import time
from smtplib import SMTP
from subprocess import Popen, PIPE

from irc import getpaths

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

TEMPLATE = u"""\
Author: {author}
Branch: {branches}
Changeset: r{rev}:{node|short}
Date: {date|isodate}
%(url)s

Log:\t{desc|fill68|tabindent}

"""


seen_nodes = set()


def check_for_local_repo(local_repo):
    return local_repo.check(dir=True)


def get_commits(service, payload):
    #XXX: service is evil, get rid
    import operator
    commits = sorted(payload['commits'],
                     key=operator.itemgetter('revision'))
    for commit in commits:
        node = commit['raw_node']
        key = service, node
        if key in seen_nodes:
            continue
        seen_nodes.add(key)
        yield commit


class BitbucketHookHandler(object):

    def send(self, from_, to, subject, body, test=False):
        from email.mime.text import MIMEText
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
            smtp = SMTP(SMTP_SERVER, SMTP_PORT)
            smtp.sendmail(from_, [to], msg.as_string())


    def send_irc_message(self, message, test=False):
        if test:
            print message + '\n'
        else:
            return subprocess.call([BOT, CHANNEL, message])

    def handle(self, payload, test=False):
        path = payload['repository']['absolute_url']
        self.payload = payload
        self.local_repo = LOCAL_REPOS.join(path)
        self.remote_repo = REMOTE_BASE + path
        if not check_for_local_repo(self.local_repo):
            print >> sys.stderr, 'Ignoring unknown repo', path
            return
        hg('pull', '-R', self.local_repo)
        self.handle_irc_message(test)
        self.handle_diff_email(test)

    USE_COLOR_CODES = True
    LISTFILES = False
    def handle_irc_message(self, test=False):
        commits = get_commits('irc', self.payload)
        if test:
            print "#" * 20
            print "IRC messages:"

        for commit in commits:
            author = commit['author']
            branch = commit['branch']
            node = commit['node']
            timestamp = commit.get('timestamp')
            print '[%s] %s %s %s' % (time.strftime('%Y-%m-%d %H:%M'), node, timestamp, author)

            files = commit.get('files', [])
            common_prefix, filenames = getpaths(files, self.LISTFILES)
            pathlen = len(common_prefix) + len(filenames) + 2
            common_prefix = '/' + common_prefix

            if self.USE_COLOR_CODES:
                author = '\x0312%s\x0F' % author   # in blue
                branch = '\x02%s\x0F'   % branch   # in bold
                node = '\x0311%s\x0F'   % node     # in azure
                common_prefix = '\x0315%s\x0F' % common_prefix # in gray

            message = commit['message'].replace('\n', ' ')
            fields = (author, branch, node, common_prefix, filenames)
            part1 = '%s %s %s %s%s: ' % fields
            totallen = 160 + pathlen
            if len(message) + len(part1) <= totallen:
                irc_msg = part1 + message
            else:
                maxlen = totallen - (len(part1) + 3)
                irc_msg = part1 + message[:maxlen] + '...'
            self.send_irc_message(irc_msg, test)

    def handle_diff_email(self, test=False):
        commits = get_commits('email', self.payload)
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
        body = hg('-R', self.local_repo, 'log', '-r', hgid,
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
            out = hg('-R', self.local_repo, 'diff', '--git', '-c', hgid,
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

    commits = [{u'author': u'arigo',
                u'branch': u'default',
                u'files': [],
                u'message': u'Merge heads.',
                u'node': u'00ae063c6b8c',
                u'parents': [u'278760e9c560', u'29f1ff96548d'],
                u'raw_author': u'Armin Rigo <arigo@tunes.org>',
                u'raw_node': u'00ae063c6b8c13d873d92afc5485671f6a944077',
                u'revision': 403,
                u'size': 0,
                u'timestamp': u'2011-01-09 13:07:24'},

               {u'author': u'antocuni',
                u'branch': u'default',
                u'files': [{u'file': u'bitbucket_hook/hook.py', u'type': u'modified'}],
                u'message': u"don't send newlines to irc",
                u'node': u'e17583fbfa5c',
                u'parents': [u'69e9eac01cf6'],
                u'raw_author': u'Antonio Cuni <anto.cuni@gmail.com>',
                u'raw_node': u'e17583fbfa5c5636b5375a5fc81f3d388ce1b76e',
                u'revision': 399,
                u'size': 19,
                u'timestamp': u'2011-01-07 17:42:13'},

               {u'author': u'antocuni',
                u'branch': u'default',
                u'files': [{u'file': u'.hgignore', u'type': u'added'}],
                u'message': u'ignore irrelevant files',
                u'node': u'5cbd6e289c04',
                u'parents': [u'3a7c89443fc8'],
                u'raw_author': u'Antonio Cuni <anto.cuni@gmail.com>',
                u'raw_node': u'5cbd6e289c043c4dd9b6f55b5ec1c8d05711c6ad',
                u'revision': 362,
                u'size': 658,
                u'timestamp': u'2010-11-04 16:34:31'},

               {u'author': u'antocuni',
                u'branch': u'default',
                u'files': [{u'file': u'bitbucket_hook/hook.py', u'type': u'modified'},
                           {u'file': u'bitbucket_hook/__init__.py', u'type': u'added'},
                           {u'file': u'bitbucket_hook/test/__init__.py',
                            u'type': u'added'},
                           {u'file': u'bitbucket_hook/test/test_hook.py',
                            u'type': u'added'}],
                u'message': u'partially refactor the hook to be more testable, and write a test for the fix in 12cc0caf054d',
                u'node': u'9c7bc068df88',
                u'parents': [u'12cc0caf054d'],
                u'raw_author': u'Antonio Cuni <anto.cuni@gmail.com>',
                u'raw_node': u'9c7bc068df8850f4102c610d2bee3cdef67b30e6',
                u'revision': 391,
                u'size': 753,
                u'timestamp': u'2010-12-19 14:45:44'}]


    test_payload[u'commits']  = commits

##    # To regenerate:
##    try:
##        from json import loads # 2.6
##    except ImportError:
##        from simplejson import loads
##
##    from urllib2 import urlopen
##    url = ("https://api.bitbucket.org/1.0/repositories/pypy/buildbot/"
##           "changesets/%s/")
##
##    # Representative changesets
##    mergeheads = u'00ae063c6b8c'
##    singlefilesub = u'e17583fbfa5c'
##    root = u'5cbd6e289c04'
##    multiadd = u'9c7bc068df88'
##    test_nodes = mergeheads, singlefilesub, root, multiadd
##
##    commits = []
##    for commit in test_nodes:
##        req = urlopen(url % commit)
##        payload = req.read()
##        req.close()
##        commits.append(loads(payload))
##
##    test_payload['commits'] = commits

    LOCAL_REPOS = py.path.local(repopath)

    hook = BitbucketHookHandler()
    hook.USE_COLOR_CODES = False
    hook.handle(test_payload, test=True)
