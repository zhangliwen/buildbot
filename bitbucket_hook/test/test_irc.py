from bitbucket_hook.irc import getpaths

def fl(*paths):
    return [{'file': x} for x in paths]

def test_getpaths():
    d = dict
    barefile = fl('file')
    distinct = fl('path1/file1', 'path2/file2', 'path3/file')
    shared = fl('path/file1', 'path/file2', 'path/file')

    deepfile = fl('a/long/path/to/deepfile.py')
    slashesfile = fl('/slashesfile/')
    slashleft = fl('/slashleft')
    slashright = fl('slashright/')


    nocommon = distinct + fl('path4/file')
    nocommonplusroot = distinct + barefile

    common = fl('some/path/to/file', 'some/path/to/deeper/file',
                'some/path/to/anotherfile', 'some/path/to/afile')
    commonplusroot = shared + barefile

    empty = d(file='')
    nocommonplusempty = distinct + [empty]
    commonplusempty = shared + [empty]
    nocommonplusslash = distinct + fl('path4/dir/')
    commonplusslash = shared + fl('path/dir/')

    pypydoubleslash = fl('pypy/jit/metainterp/opt/u.py',
                         'pypy/jit/metainterp/test/test_c.py',
                         'pypy/jit/metainterp/test/test_o.py')

    pypyempty = fl('pypy/rlib/rdtoa.py', 'pypy/rlib/test/test_rdtoa.py'

    nothing = ('', '')

    # (input, expected output) for listfiles=False
    files_expected = [([], nothing),
                      ([empty], nothing),
                      ([empty, empty], nothing),
                      (barefile, ('file', '')),
                      (deepfile, ('a/long/path/to/deepfile.py', '')),
                      (slashesfile, ('/slashesfile/', '')),
                      (slashleft, ('/slashleft', '')),
                      (slashright, ('slashright/', '')),
                      (nocommon, nothing),
                      (nocommonplusroot, nothing),
                      (nocommonplusempty, nothing),
                      (common, ('some/path/to/', '')),
                      (commonplusroot, nothing),
                      (commonplusempty, nothing),
                      (nocommonplusslash, nothing),
                      (commonplusslash, ('path/', '')),
                      (pypydoubleslash, ('pypy/jit/metainterp/', '')),
                      (pypyempty, ('pypy/rlib/', '')),
                      ]

    for f, wanted in files_expected:
        assert getpaths(f) == wanted

    # (input, expected output) for listfiles=True
    files_expected = [([], nothing),
                      ([empty], nothing),
                      ([empty, empty], nothing),
                      (barefile, ('file', '')),
                      (deepfile, ('a/long/path/to/deepfile.py', '')),
                      (slashesfile, ('/slashesfile/', '')),
                      (slashleft, ('/slashleft', '')),
                      (slashright, ('slashright/', '')),
                      (nocommon, ('', ' M(file1, file2, file, file)')),
                      (nocommonplusroot, ('', ' M(file1, file2, file, file)')),
                      (nocommonplusempty, ('',' M(file1, file2, file)')),
                      (common, ('some/path/to/',
                                ' M(file, file, anotherfile, afile)')),
                      (commonplusroot, ('', ' M(file1, file2, file, file)')),
                      (commonplusempty, ('',' M(file1, file2, file)')),
                      (nocommonplusslash, ('',' M(file1, file2, file)')),
                      (commonplusslash, ('path/',' M(file1, file2, file)')),
                      (pypydoubleslash, ('pypy/jit/metainterp/',
                                         ' M(u.py, test_c.py, test_o.py)')),
                      (pypyempty, ('pypy/rlib/',
                                   ' M(rdtoa.py, test_rdtoa.py)')),
                      ]

    for f, wanted in files_expected:
        assert getpaths(f, listfiles=True) == wanted


