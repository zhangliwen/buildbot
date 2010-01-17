import os

class jstests_setup(object):
    staticDirs = {
       '/js': os.path.join(os.path.dirname(__file__), 'js')
    }
    jsRepos = ['/js']
