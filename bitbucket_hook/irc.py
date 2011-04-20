'''
utilities for interacting with the irc bot (via cli)
'''

import os
import time
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
            app.config['BOT'], app.config['CHANNEL'], message
        ])


def handle_message(payload, test=False):
    #XXX
    from .hook import get_commits
    from .main import app
    commits = get_commits('irc', payload)
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
        common_prefix, filenames = getpaths(files, app.config['LISTFILES'])
        pathlen = len(common_prefix) + len(filenames) + 2
        common_prefix = '/' + common_prefix

        if app.config['USE_COLOR_CODES']:
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
        send_message(irc_msg, test)


