from bitbucket_hook.irc import getpaths

def fl(*paths):
    return [{'file': x} for x in paths]

def pytest_generate_tests(metafunc):

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

    empty = fl('')
    nocommonplusempty = distinct + empty
    commonplusempty = shared + empty
    nocommonplusslash = distinct + fl('path4/dir/')
    commonplusslash = shared + fl('path/dir/')

    pypydoubleslash = fl('pypy/jit/metainterp/opt/u.py',
                         'pypy/jit/metainterp/test/test_c.py',
                         'pypy/jit/metainterp/test/test_o.py')

    pypyempty = fl('pypy/rlib/rdtoa.py', 'pypy/rlib/test/test_rdtoa.py')


    nothing = ('', '')
    expectations = [
        ('null', [], nothing),
        ('empty', empty, nothing),
        ('empty*2', empty*2, nothing),
        ('bare', barefile, ('file', '')),
        ('deep', deepfile, ('a/long/path/to/deepfile.py', '')),
        ('slashes', slashesfile, ('/slashesfile/', '')),
        ('slashleft', slashleft, ('/slashleft', '')),
        ('slashright', slashright, ('slashright/', '')),
        ('nocommon', nocommon, ('', ' M(file1, file2, file, file)')),
        ('nocommon+root', nocommonplusroot, 
                          ('', ' M(file1, file2, file, file)')),
        ('nocommon+empty', nocommonplusempty, ('',' M(file1, file2, file)')),
        ('common', common, ('some/path/to/',
                ' M(file, file, anotherfile, afile)')),
        ('common+root', commonplusroot, ('', ' M(file1, file2, file, file)')),
        ('common+empty', commonplusempty, ('',' M(file1, file2, file)')),
        ('nocommon+slash', nocommonplusslash, ('',' M(file1, file2, file)')),
        ('common+slash', commonplusslash, ('path/',' M(file1, file2, file)')),
        ('pypydoubledash', pypydoubleslash, ('pypy/jit/metainterp/',
                         ' M(u.py, test_c.py, test_o.py)')),
        ('pypyempty', pypyempty, ('pypy/rlib/',
                   ' M(rdtoa.py, test_rdtoa.py)')),
        ]

    if metafunc.function.__name__=='test_getpaths':
        for name, files, (common, listfiles) in expectations:
            metafunc.addcall(id='list/'+name, funcargs={
                'files': files,
                'expected_common': common,
                'expected_listfiles': listfiles,
            })
            metafunc.addcall(id='nolist/'+name, funcargs={
                'files': files,
                'expected_common': common,
                'expected_listfiles': listfiles,
            })


def test_getpaths(files, expected_common, expected_listfiles):
    common, files = getpaths(files, listfiles=bool(expected_listfiles))
    assert common == expected_common
    assert files == expected_listfiles


