import py
from pypybuildbot import builds

class FakeProperties(object):
    def __getitem__(self, item):
        if item == 'branch':
            return None
    
    def render(self, x):
        return x

class FakePropertyBuilder(object):
    slaveEnvironment = None
    
    def getProperties(self):
        return FakeProperties()

    def getSlaveCommandVersion(self, *args):
        return 3

class FakeStepStatus(object):
    def setText(self, *args):
        pass

class FakeDeferred(object):
    def addCallback(self, *args):
        return FakeDeferred()
    def addErrback(self, *args):
        return FakeDeferred()

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

def test_pypy_upload():
    pth = py.test.ensuretemp('buildbot')
    inst = builds.PyPyUpload(slavesrc='slavesrc', masterdest=str(pth.join('mstr')),
                             basename='base', workdir='.',
                             blocksize=100)
    factory, kw = inst.factory
    rebuilt = factory(**kw)
    rebuilt.build = FakePropertyBuilder()
    rebuilt.step_status = FakeStepStatus()
    rebuilt.runCommand = lambda *args: FakeDeferred()
    rebuilt.start()
    assert pth.join('mstr').check(dir=True)
