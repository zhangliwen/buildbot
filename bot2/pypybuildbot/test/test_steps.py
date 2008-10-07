from pypybuildbot import steps


def test_Translate():
    expected = ['translate.py', '--batch', '-O0',
                'targetpypystandalone', '--no-allworkingmodules']

    translateInst = steps.Translate(['-O0'], ['--no-allworkingmodules'])

    assert translateInst.command[-len(expected):] == expected
    
    translateFactory, kw = translateInst.factory
    rebuiltTranslate = translateFactory(**kw)
                
    assert rebuiltTranslate.command[-len(expected):] == expected
