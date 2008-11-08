from pypybuildbot import builds
import os, py

def test_Translate():
    expected = ['translate.py', '--batch', '-O0',
                'targetpypystandalone', '--no-allworkingmodules']

    translateInst = builds.Translate(['-O0'], ['--no-allworkingmodules'])

    assert translateInst.command[-len(expected):] == expected
    
    translateFactory, kw = translateInst.factory
    rebuiltTranslate = translateFactory(**kw)
                
    assert rebuiltTranslate.command[-len(expected):] == expected

def test_scratchbox():
    factory = builds.PyPyTranslatedScratchboxTestFactory()
    user = py.path.local(os.environ['HOME']).basename
    for step in factory.steps:
        assert step[1]['workdir'].startswith('/scratchbox/users/%s/home/%s' %
                                             (user, user))

