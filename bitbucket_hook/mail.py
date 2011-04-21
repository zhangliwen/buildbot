from . import scm
from smtplib import SMTP


TEMPLATE = u"""\
Author: {author}
Branch: {branches}
Changeset: r{rev}:{node|short}
Date: {date|isodate}
%(url)s

Log:\t{desc|fill68|tabindent}

"""

def handle_commit(payload, commit):
    return send_diff_for_commit(payload, commit)


def send_diff_for_commit(payload, commit, test=False):
    from .main import app

    path = payload['repository']['absolute_url']
    local_repo = app.config['LOCAL_REPOS'].join(path)
    remote_repo = app.config['REMOTE_BASE'] + path

    hgid = commit['raw_node']
    sender = commit['author'] + ' <commits-noreply@bitbucket.org>'
    lines = commit['message'].splitlines()
    line0 = lines and lines[0] or ''
    reponame = payload['repository']['name']
    # TODO: maybe include the modified paths in the subject line?
    url = remote_repo + 'changeset/' + commit['node'] + '/'
    template = TEMPLATE % {'url': url}
    subject = '%s %s: %s' % (reponame, commit['branch'], line0)
    body = scm.hg('-R', local_repo, 'log', '-r', hgid,
             '--template', template)
    diff = scm.get_diff(local_repo, hgid, commit['files'])
    body = body + diff
    send(sender, app.config['ADDRESS'], subject, body, test)


def send(from_, to, subject, body, test=False):
    from .main import app
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
        smtp = SMTP(app.config['SMTP_SERVER'], app.config['SMTP_PORT'])
        smtp.sendmail(from_, [to], msg.as_string())

