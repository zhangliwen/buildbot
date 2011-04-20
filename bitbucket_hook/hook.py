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

    app.config['LOCAL_REPOS'] = py.path.local(repopath)
    app.config['USE_COLOR_CODES'] = False

    handle(test_payload, test=True)
