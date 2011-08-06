'''
utilities for interacting with the irc bot (via cli)
'''

import os
import subprocess

def getpaths(files, listfiles=False):

    # Handle empty input
    if not files:
        return '', ''
    files = [f['file'] for f in files]
    if not any(files):
        return '', ''

    dirname = os.path.dirname
    basename = os.path.basename

    common_prefix = [dirname(f) for f in files]

    # Single file, show its full path
    if len(files) == 1:
        common_prefix = files[0]
        listfiles = False

    else:
        common_prefix = [path.split(os.sep) for path in common_prefix]
        common_prefix = os.sep.join(os.path.commonprefix(common_prefix))
        if common_prefix and not common_prefix.endswith('/'):
            common_prefix += '/'

    if listfiles:
        # XXX Maybe should return file paths relative to prefix? Or TMI?
        filenames = [basename(f) for f in files if f and basename(f)]
        filenames = ' M(%s)' % ', '.join(filenames)
    else:
        filenames = ''
    return common_prefix, filenames


def send_message(message, test=False):
    if test:
        print message + '\n'
    else:
        from .main import app
        return subprocess.call([
            app.config['BOT'],
            app.config['CHANNEL'],
            message,
        ])

def get_short_id(owner, repo, branch):
    """
    Custom rules to get a short string that identifies a repo/branch in a
    useful way, for IRC messages.  Look at test_irc.test_get_short_id for what
    we expect.
    """
    from .main import app
    repo_parts = []
    if owner != app.config['DEFAULT_USER']:
        repo_parts.append('%s' % owner)
    if repo_parts or repo != app.config['DEFAULT_REPO']:
        repo_parts.append(repo)
    repo_id = '/'.join(repo_parts)
    #
    if repo_id == '':
        return branch
    elif branch == 'default':
        return repo_id
    elif repo_id == branch:
        return repo_id # e.g., pypy/extradoc has a branch extradoc, just return 'extradoc'
    else:
        return '%s[%s]' % (repo_id, branch)
    return branch


def handle_commit(payload, commit, test=False):
    from .main import app

    repo_owner = payload['repository']['owner']
    repo_name = payload['repository']['name']
    author = commit['author']
    branch = commit['branch']
    node = commit['node']
    short_id = get_short_id(repo_owner, repo_name, branch)

    files = commit.get('files', [])
    common_prefix, filenames = getpaths(files, app.config['LISTFILES'])
    pathlen = len(common_prefix) + len(filenames) + 2
    common_prefix = '/' + common_prefix

    if app.config['USE_COLOR_CODES']:
        author = '\x0312%s\x0F' % author   # in blue
        short_id = '\x02%s\x0F' % short_id   # in bold
        node = '\x0311%s\x0F' % node     # in azure
        common_prefix = '\x0315%s\x0F' % common_prefix  # in gray

    message = commit['message'].replace('\n', ' ')
    fields = (author, short_id, node, common_prefix, filenames)
    part1 = '%s %s %s %s%s: ' % fields
    totallen = 160 + pathlen
    if len(message) + len(part1) <= totallen:
        irc_msg = part1 + message
    else:
        maxlen = totallen - (len(part1) + 3)
        irc_msg = part1 + message[:maxlen] + '...'
    send_message(irc_msg, test)
