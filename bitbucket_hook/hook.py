import os.path
import py
import subprocess
import sys
import time

from . import irc
from .main import app

from . import scm
from . import mail


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


def handle(payload, test=False):
    path = payload['repository']['absolute_url']
    local_repo = app.config['LOCAL_REPOS'].join(path)
    remote_repo = app.config['REMOTE_BASE'] + path
    if not check_for_local_repo(local_repo):
        print >> sys.stderr, 'Ignoring unknown repo', path
        return
    scm.hg('pull', '-R', local_repo)
    irc.handle_message(payload, test)
    mail.handle_diff_email(payload, test)
