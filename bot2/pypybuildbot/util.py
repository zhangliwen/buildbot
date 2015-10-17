import os
import socket
from datetime import datetime, timedelta

def we_are_debugging():
    return socket.gethostname() != 'cobra'

def load(name):
    mod = __import__(name, {}, {}, ['__all__'])
    reload(mod)
    return mod

def symlink_force(src, dst):
    """
    More or less equivalent to "ln -fs": it overwrites the destination, if it
    exists
    """
    if os.path.lexists(dst):
        os.remove(dst)
    os.symlink(src, dst)

def clean_old_files(dest, oldest_in_days):
    '''
    remove files from dest older than 'older_in_days' days
    and remove empty directories as well
    '''

    old_hours = 24 * oldest_in_days
    for dirpath, dirnames, filenames in os.walk(dest):
        for fname in filenames:
            curpath = os.path.join(dirpath, fname)
            mtime = datetime.fromtimestamp(os.path.getmtime(curpath))
            if datetime.now() - mtime > timedelta(hours=old_hours):
                os.remove(curpath)
        if len(filenames) == 0:
            os.rmdir(dirpath)
 
