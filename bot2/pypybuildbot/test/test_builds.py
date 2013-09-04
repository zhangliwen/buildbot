import py
from cStringIO import StringIO
from pypybuildbot import builds

class FakeProperties(object):

    def __init__(self):
        pass
    
    def __getitem__(self, item):
        if item == 'branch':
            return None
        if item == 'got_revision':
            return 123
        if item == 'final_file_name':
            return '123-ea5ca8'
    
    def render(self, x):
        return x

class FakeBuild(object):
    slaveEnvironment = None

    def __init__(self):
        self.properties = FakeProperties()
    
    def getProperties(self):
        return self.properties

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
    expected = ['pypy', '../../rpython/bin/rpython', '--batch', '-O0',
                'targetpypystandalone', '--no-allworkingmodules']

    translateInst = builds.Translate(['-O0'], ['--no-allworkingmodules'])

    assert translateInst.command[-len(expected):] == expected
    
    translateFactory = translateInst._getStepFactory().factory
    args = translateInst._getStepFactory().args
    rebuiltTranslate = translateFactory(*args)
                
    assert rebuiltTranslate.command[-len(expected):] == expected

    rebuiltTranslate.build = FakeBuild()
    rebuiltTranslate.setBuild(rebuiltTranslate.build)
    rebuiltTranslate.startCommand = lambda *args: None
    rebuiltTranslate.start()

def test_pypy_upload():
    pth = py.test.ensuretemp('buildbot')
    inst = builds.PyPyUpload(slavesrc='slavesrc', masterdest=str(pth.join('mstr')),
                             basename='base-%(final_file_name)s', workdir='.',
                             blocksize=100)
    factory = inst._getStepFactory().factory
    kw = inst._getStepFactory().kwargs
    rebuilt = factory(**kw)
    rebuilt.build = FakeBuild()
    rebuilt.step_status = FakeStepStatus()
    rebuilt.runCommand = lambda *args: FakeDeferred()
    rebuilt.start()
    assert pth.join('mstr').check(dir=True)
    assert rebuilt.masterdest == str(pth.join('mstr', 'trunk',
                                              'base-123-ea5ca8'))
    assert rebuilt.symlinkname == str(pth.join('mstr', 'trunk',
                                               'base-latest'))

class TestPytestCmd(object):
    
    class Fake(object):
        def __init__(self, **kwds):
            self.__dict__.update(kwds)

    class FakeBuildStatus(Fake):
        def getProperties(self):
            return self.properties

    class FakeBuilder(Fake):
        def saveYourself(self):
            pass

    def _create(self, log, rev, branch):
        if isinstance(log, str):
            log = StringIO(log)
        step = builds.PytestCmd()
        step.build = self.Fake()
        step.build.build_status = self.FakeBuildStatus(properties={'got_revision': rev,
                                                                   'branch': branch})
        step.build.build_status.builder = builder = self.FakeBuilder()
        cmd = self.Fake(logs={'pytestLog': log})
        return step, cmd, builder

    def test_no_log(self):
        step = builds.PytestCmd()
        cmd = self.Fake(logs={})
        assert step.commandComplete(cmd) is None

    def test_empty_log(self):
        step, cmd, builder = self._create(log='', rev='123', branch='trunk')
        step.commandComplete(cmd)
        summary = builder.summary_by_branch_and_revision[('trunk', '123')]
        assert summary.to_tuple() == (0, 0, 0, 0)

    def test_summary(self):
        log = """F a/b.py:test_one
. a/b.py:test_two
s a/b.py:test_three
S a/c.py:test_four
"""
        step, cmd, builder = self._create(log=log, rev='123', branch='trunk')
        step.commandComplete(cmd)
        summary = builder.summary_by_branch_and_revision[('trunk', '123')]
        assert summary.to_tuple() == (1, 1, 2, 0)

    def test_branch_is_None(self): 
        step, cmd, builder = self._create(log='', rev='123', branch=None)
        step.commandComplete(cmd)
        assert ('trunk', '123') in builder.summary_by_branch_and_revision

    def test_trailing_slash(self):
        step, cmd, builder = self._create(log='', rev='123', branch='branch/foo/')
        step.commandComplete(cmd)
        assert ('branch/foo', '123') in builder.summary_by_branch_and_revision
        
    def test_multiple_logs(self):
        log = """F a/b.py:test_one
. a/b.py:test_two
s a/b.py:test_three
S a/c.py:test_four
"""
        step, cmd, builder = self._create(log=log, rev='123', branch='trunk')
        step.commandComplete(cmd)
        cmd.logs['pytestLog'] = StringIO(log) # "reopen" the file
        step.commandComplete(cmd)
        summary = builder.summary_by_branch_and_revision[('trunk', '123')]
        assert summary.to_tuple() == (2, 2, 4, 0)
