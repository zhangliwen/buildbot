from pypybuildbot import builds

class FakeProperties(object):
    def render(self, x):
        return x

class FakePropertyBuilder(object):
    slaveEnvironment = None
    
    def getProperties(self):
        return FakeProperties()

def test_Translate():
    expected = ['translate.py', '--batch', '-O0',
                'targetpypystandalone', '--no-allworkingmodules']

    translateInst = builds.Translate(['-O0'], ['--no-allworkingmodules'])

    assert translateInst.command[-len(expected):] == expected
    
    translateFactory, kw = translateInst.factory
    rebuiltTranslate = translateFactory(**kw)
                
    assert rebuiltTranslate.command[-len(expected):] == expected

    rebuiltTranslate.build = FakePropertyBuilder()
    rebuiltTranslate.startCommand = lambda *args: None
    rebuiltTranslate.start()
