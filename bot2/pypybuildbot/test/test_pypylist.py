from pypybuildbot.pypylist import PyPyTarball

def test_pypytarball():
    t = PyPyTarball('pypy-c-jit-75654-linux.tar.bz2')
    assert t.filename == 'pypy-c-jit-75654-linux.tar.bz2'
    assert t.exe == 'pypy'
    assert t.backend == 'c'
    assert t.features == 'jit'
    assert t.rev == '75654'
    assert t.platform == 'linux'

def test_invalid_filename():
    t = PyPyTarball('foo')
    assert t.filename == 'foo'
    assert t.exe == None
    assert t.backend == None
    assert t.features == None
    assert t.rev == -1
    assert t.platform == None
    t2 = PyPyTarball('pypy-c-jit-75654-linux.tar.bz2')
    assert t < t2

def test_sort():
    files = map(PyPyTarball, [
            'pypy-c-jit-10000-linux.tar.bz2',
            'pypy-c-jit-20000-linux.tar.bz2',
            'pypy-c-nojit-10000-linux.tar.bz2',
            'pypy-c-jit-10000-linux64.tar.bz2',
            'pypy-c-jit-10000-win32.tar.bz2',
            'pypy-c-stackless-10000-linux.tar.bz2',
            ])

    files.sort(key=PyPyTarball.key, reverse=True)
    files = [f.filename for f in files]
    assert files == [
        'pypy-c-jit-20000-linux.tar.bz2',
        'pypy-c-jit-10000-linux.tar.bz2',
        'pypy-c-jit-10000-linux64.tar.bz2',
        'pypy-c-jit-10000-win32.tar.bz2',
        'pypy-c-nojit-10000-linux.tar.bz2',
        'pypy-c-stackless-10000-linux.tar.bz2',
        ]

def test_builder_names():
    t = PyPyTarball('pypy-c-jit-76867-linux.tar.bz2')
    assert t.get_builder_names() == ('own-linux-x86-32',
                                     'pypy-c-jit-linux-x86-32')

    t = PyPyTarball('pypy-c-nojit-76867-linux.tar.bz2')
    assert t.get_builder_names() == ('own-linux-x86-32',
                                     'pypy-c-app-level-linux-x86-32')
    
    t = PyPyTarball('pypy-c-stackless-76867-linux.tar.bz2')
    assert t.get_builder_names() == ('own-linux-x86-32',
                                     'pypy-c-stackless-app-level-linux-x86-32')

    t = PyPyTarball('pypy-c-jit-76867-osx.tar.bz2')
    assert t.get_builder_names() == ('own-macosx-x86-32',
                                     'pypy-c-jit-macosx-x86-32')

    t = PyPyTarball('pypy-c-jit-76867-linux64.tar.bz2')
    assert t.get_builder_names() == ('own-linux-x86-64',
                                     'pypy-c-jit-linux-x86-64')

    t = PyPyTarball('pypy-c-jit-76867-win32.tar.bz2')
    assert t.get_builder_names() == ('own-win-x86-32',
                                     'pypy-c-jit-win-x86-32')
