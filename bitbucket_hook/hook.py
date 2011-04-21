import os.path
import py
import subprocess
import sys
import time

from . import irc
from .main import app

from . import scm
from . import mail


def check_for_local_repo(local_repo):
    return local_repo.check(dir=True)

def get_commits(payload, seen_nodes=set()):
    import operator
    commits = sorted(payload['commits'],
                     key=operator.itemgetter('revision'))
    for commit in commits:
        node = commit['raw_node']
        if node in seen_nodes:
            continue
        seen_nodes.add(node)
        yield commit


def handle(payload, test=False):
    path = payload['repository']['absolute_url']
    local_repo = app.config['LOCAL_REPOS'].join(path)
    remote_repo = app.config['REMOTE_BASE'] + path
    if not check_for_local_repo(local_repo):
        print >> sys.stderr, 'Ignoring unknown repo', path
        return
    scm.hg('pull', '-R', local_repo)
    for commit in get_commits(payload):
        irc.handle_commit(payload, commit, test)
        mail.handle_commit(payload, commit, test)
