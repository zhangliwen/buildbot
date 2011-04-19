'''
utilities for interacting with the irc bot (via cli)
'''

import os

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
