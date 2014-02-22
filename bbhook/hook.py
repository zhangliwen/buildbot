import os.path
import py
import subprocess
import sys
import time
import thread, Queue
import traceback
import pprint

from .main import app
from . import scm
#
from . import stdoutlog
from . import irc
from . import mail


HANDLERS = [
    stdoutlog.handle_commit,
    irc.handle_commit,
    mail.handle_commit
    ]

def check_for_local_repo(local_repo, remote_repo, owner):
    if local_repo.check(dir=True):
        return True
    if owner == app.config['DEFAULT_USER']:
        print >> sys.stderr, 'Automatic initial clone of %s' % remote_repo
        scm.hg('clone', str(remote_repo), str(local_repo))
        return True
    return False

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



def _handle_thread():
    while True:
        local_repo = payload = None
        try:
            local_repo, payload = queue.get()
            _do_handle(local_repo, payload)
        except:
            traceback.print_exc()
            print >> sys.stderr, 'payload:'
            pprint.pprint(payload, sys.stderr)
            print >> sys.stderr

queue = Queue.Queue()
thread.start_new_thread(_handle_thread, ())


def handle(payload, test=True):
    path = payload['repository']['absolute_url']
    owner = payload['repository']['owner']
    local_repo = app.config['LOCAL_REPOS'].join(path)
    remote_repo = app.config['REMOTE_BASE'] + path
    if not check_for_local_repo(local_repo, remote_repo, owner):
        print >> sys.stderr, 'Ignoring unknown repo', path
        return
    if test:
        _do_handle(local_repo, payload, test)
    else:
        queue.put((local_repo, payload))

def _do_handle(local_repo, payload, test=False):
    scm.hg('pull', '-R', local_repo)
    for commit in get_commits(payload):
        for handler in HANDLERS:
            handler(payload, commit, test)
