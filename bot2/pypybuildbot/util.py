import os
import socket

def we_are_debugging():
    return socket.gethostname() != 'baroquesoftware'

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

def isRPython(change):
    for fname in change.files:
        if fname.startswith('rpython'):
            log.msg('fileIsImportant filter isRPython got "%s"' % fname)
            return True
    return False
