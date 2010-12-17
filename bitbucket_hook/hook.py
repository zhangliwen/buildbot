import socket
import sys
import py

LOCAL_REPOS = py.path.local(__file__).dirpath('repos')
REMOTE_BASE = 'http://bitbucket.org'

if socket.gethostname() == 'viper':
    # for debugging, antocuni's settings
    SMTP_SERVER = "out.alice.it"
    SMTP_PORT = 25
    ADDRESS = 'anto.cuni@gmail.com'
else:
    # real settings, (they works on codespeak at least)
    SMTP_SERVER = 'localhost'
    SMTP_PORT = 25
    ADDRESS = 'pypy-svn@codespeak.net'

hg = py.path.local.sysfind('hg').sysexec

def send(from_, to, subject, body):
    import smtplib
    from email.mime.text import MIMEText

    smtp = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    msg = MIMEText(body)
    msg['From'] = from_
    msg['To'] = to
    msg['Subject'] = subject
    smtp.sendmail(from_, [to], msg.as_string())

template = """\
Author: {author}
Branch: {branches}
Changeset: {node|short}
Date: {date|isodate}
Log:
\t{desc|tabindent}

"""

class BitbucketHookHandler(object):

    def handle(self, payload):
        path = payload['repository']['absolute_url']
        self.payload = payload
        self.local_repo = LOCAL_REPOS.join(path)
        self.remote_repo = REMOTE_BASE + path
        if not self.local_repo.check(dir=True):
            print >> sys.stderr, 'Ignoring unknown repo', path
            return
        hg('pull', '-R', self.local_repo)
        self.handle_diff_email()

    def handle_diff_email(self):
        for commit in payload['commits']:
            self.send_diff_for_commit(commit)

    def send_diff_for_commit(self, commit):
        hgid = commit['raw_node']
        sender = commit['author'] + ' <commits-noreply@bitbucket.org>'
        lines = commit['message'].splitlines()
        line0 = lines and lines[0] or ''
        reponame = self.payload['repository']['name']
        # TODO: maybe include the modified paths in the subject line?
        subject = '%s %s: %s' % (reponame, commit['branch'], line0)
        body = hg('-R', self.local_repo, 'log', '-r', hgid,
                 '--template', template)
        diff = self.get_diff(hgid, commit['files'])
        body = body+diff
        send(sender, ADDRESS, subject, body)

    def get_diff(self, hgid, files):
        import re
        binary = re.compile('^GIT binary patch$', re.MULTILINE)
        files = [item['file'], item['type'] for item in files]
        lines = []
        status_lines = []
        for filename, status in files:
            status = status[0].upper()
            out = hg('-R', self.local_repo, 'diff', '--git', '-c', hgid,
                     self.local_repo.join(filename))
            match = binary.search(out)
            if match:
                # it's a binary patch, omit the content
                out = out[:match.end()]
                out += '\n[cut]'
            lines.append(out)
        return '\n'.join(lines)


if __name__ == '__main__':
    payload = {u'commits': [{u'author': u'antocuni',
                             u'branch': u'default',
                             u'files': [{u'file': u'pdbdemo2.py', u'type': u'modified'},
                                        {u'file': u'README2', u'type': u'added'},
                                        {u'file': u'xx.png', u'type': u'added'}],
                             u'message': u'test for git diff',
                             u'node': u'81d52c8e34ba',
                             u'parents': [u'3d60a8c359a3'],
                             u'raw_node': u'81d52c8e34ba44bd34780906064eee12b81cb82b',
                             u'revision': 21,
                             u'size': 2439,
                             u'timestamp': u'2010-12-17 12:00:24'},

                            {u'author': u'antocuni',
                             u'branch': u'default',
                             u'files': [{u'file': u'pdbdemo2.py', u'type': u'modified'},
                                        {u'file': u'README2', u'type': u'modified'}],
                             u'message': u'Chapter 11. Customizing the output of Mercurial\n\nTable of Contents\n\nLoad all comments (slow)\n\nUsing precanned output styles\n\n    Setting a default style\n\nCommands that support styles and templates\nThe basics of templating\nCommon template keywords\nEscape sequences\nFiltering keywords to change their results',
                             u'node': u'47b731b0f331',
                             u'parents': [u'e26b0d04f68e'],
                             u'raw_node': u'47b731b0f3312ab3302f4b45f1ec28292f6a2bcc',
                             u'revision': 24,
                             u'size': 1141,
                             u'timestamp': u'2010-12-17 14:28:12'}],
               u'repository': {u'absolute_url': u'/antocuni/test/',
                               u'name': u'test',
                               u'owner': u'antocuni',
                               u'slug': u'test',
                               u'website': u''},
               u'user': u'antocuni'}

    hook = BitbucketHookHandler()
    hook.handle(payload)
