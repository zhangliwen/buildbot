from twisted.web.static import File
import re

# to get the desired order keep in mind that they are reversed at the end, so
# the highest the value, the bigger the priority
FEATURES = {
    'jit':      100,
    'nojit':     50,
    'stackless': 10
    }

PLATFORMS = {
    'linux':    100,
    'linux64':   50,
    'win32':     10,
    }

def parsename(name):
    # name is something like pypy-c-jit-75654-linux.tar.bz2
    try:
        name2 = name.replace('.tar.bz2', '')
        exe, backend, features, rev, platform = name2.split('-')
    except ValueError:
        return '', name
    else:
        return rev, PLATFORMS.get(platform, -1), FEATURES.get(features, -1), name

class PyPyList(File):

    def listNames(self):
        names = File.listNames(self)
        items = map(parsename, names)
        items.sort()
        items.reverse()
        return [item[-1] for item in items]

