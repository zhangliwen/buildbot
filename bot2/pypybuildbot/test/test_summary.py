from zope.interface import implements
from buildbot import interfaces as buildbot_intefaces
from buildbot.status import builder as status_builder
from buildbot.process import builder as process_builder
from buildbot.process import factory as process_factory
from pypybuildbot import summary
from StringIO import StringIO
import re

class TestOutcomes(object):

    def test_populate(self):
        rev_outcome_set = summary.RevisionOutcomeSet(50000, ('foo', 40))

        assert rev_outcome_set.revision == 50000
        assert rev_outcome_set.key == ('foo', 40)

        log = StringIO("""F a/b.py:test_one
. a/b.py:test_two
s a/b.py:test_three
""")
        
        rev_outcome_set.populate(log)

        assert rev_outcome_set.skipped == set([("a.b","test_three")])
        assert rev_outcome_set.failed == set([("a.b", "test_one")])
        assert rev_outcome_set.numpassed == 1

        res = rev_outcome_set.get_outcome(("a.b", "test_one"))
        assert res == 'F'
        key_namekey = rev_outcome_set.get_key_namekey(("a.b", "test_one"))
        assert key_namekey == (('foo', 40), ("a.b", "test_one"))

        res = rev_outcome_set.get_outcome(("a.b", "test_three"))
        assert res == 's'
        key_namekey = rev_outcome_set.get_key_namekey(("a.b", "test_three"))
        assert key_namekey == (('foo', 40), ("a.b", "test_three"))

        res = rev_outcome_set.get_outcome(("a.b", "test_two"))
        assert res == '.'

    def test_populate_from_empty(self):
        rev_outcome_set = summary.RevisionOutcomeSet(0)
        log = StringIO("")
        rev_outcome_set.populate(log)
        
    def test_populate_longrepr(self):
        rev_outcome_set = summary.RevisionOutcomeSet(50000)
        log = StringIO("""F a/b.py:test_one
 some
 traceback
. a/b.py:test_two
s a/b.py:test_three
 some skip
""")
        
        rev_outcome_set.populate(log)

        assert len(rev_outcome_set.skipped) == 1
        assert len(rev_outcome_set.failed) == 1
        assert rev_outcome_set.numpassed == 1

        assert rev_outcome_set.longreprs == {
("a.b","test_three"): "some skip\n",
("a.b", "test_one"): "some\ntraceback\n"
            }

        res = rev_outcome_set.get_longrepr(("a.b", "test_two"))
        assert res == ''

        res = rev_outcome_set.get_longrepr(("a.b", "test_one"))
        assert res == "some\ntraceback\n"

    def test_populate_encodings(self):
        rev_outcome_set = summary.RevisionOutcomeSet(50000)
        log = StringIO("""F a/b.py:test_one
 \xe5 foo
F a/b.py:test_two
 \xc3\xa5 bar
""")
        
        rev_outcome_set.populate(log)

        assert len(rev_outcome_set.failed) == 2
        assert rev_outcome_set.numpassed == 0

        assert rev_outcome_set.longreprs == {
("a.b","test_one"): u"\xe5 foo\n",
("a.b", "test_two"): u"\xe5 bar\n"
            }

    def test_populate_special(self):
        rev_outcome_set = summary.RevisionOutcomeSet(50000)
        log = StringIO("""F a/b.py
s a/c.py
! <run>
! /a/b/c.py:92
""")
        
        rev_outcome_set.populate(log)

        assert rev_outcome_set.failed == set([
            ("a.b", ''),
            ("<run>", ''),
            ("/a/b/c.py:92", '')])

        assert rev_outcome_set.skipped == set([
            ("a.c", '')])

        assert rev_outcome_set.numpassed == 0
        
    def test_absent_outcome(self):
        rev_outcome_set = summary.RevisionOutcomeSet(50000)

        res = rev_outcome_set.get_outcome(('a', 'b'))
        assert res == ' '

    def test_RevisionOutcomeSetCache(self):
        cache = summary.RevisionOutcomeSetCache(cachesize=3)
        calls = []
        def load(x, y):
            calls.append(y)
            return y
        
        cache._load_outcome_set = load

        res = cache.get('status', 'a')
        assert res == 'a'
        cache.get('status', 'b')
        cache.get('status', 'c')

        assert calls == ['a', 'b', 'c']

        cache.get('status', 'a')
        cache.get('status', 'b')
        res = cache.get('status', 'c')
        assert res == 'c'
        
        assert calls == ['a', 'b', 'c']

        calls = []
        res = cache.get('status', 'd')
        assert res == 'd'
        assert cache.get('status', 'c') == 'c'
        assert cache.get('status', 'b') == 'b'        
        assert calls == ['d']

        res = cache.get('status', 'a')
        assert res == 'a'

        assert calls == ['d', 'a']

    def test_GatherOutcomeSet(self):
        key_foo = ('foo', 3)
        rev_outcome_set_foo = summary.RevisionOutcomeSet(50000, key_foo)
        log = StringIO("""F a/b.py:test_one
 some
 traceback
. a/b.py:test_two
s a/b.py:test_three
""")
        
        rev_outcome_set_foo.populate(log)


        key_bar = ('bar', 7)        
        rev_outcome_set_bar = summary.RevisionOutcomeSet(50000,
                                                         key_bar)
        log = StringIO(""". a/b.py:test_one
. a/b.py:test_two
s a/b.py:test_three
""")
        
        rev_outcome_set_bar.populate(log)

        d = {'foo': rev_outcome_set_foo,
             'bar': rev_outcome_set_bar}

        goutcome = summary.GatherOutcomeSet(d)

        assert goutcome.revision == 50000
        
        assert goutcome.failed == set([('foo', 'a.b', 'test_one')])
        assert goutcome.failed == set([('foo', 'a.b', 'test_one')])

        assert goutcome.skipped == set([('foo', 'a.b', 'test_three'),
                                        ('bar', 'a.b', 'test_three'),
                                        ])
        assert goutcome.skipped == set([('foo', 'a.b', 'test_three'),
                                        ('bar', 'a.b', 'test_three'),
                                        ])
        assert goutcome.numpassed == 3

        for prefix in ('foo', 'bar'):
            for mod, testname in (("a.b", "test_one"), ("a.b", "test_two"),
                                  ("a.b", "test_three")):

                outcome1 = d[prefix].get_outcome((mod, testname))
                outcome2 = goutcome.get_outcome((prefix, mod, testname))
                assert outcome2 == outcome1

                key_namekey1 = d[prefix].get_key_namekey((mod, testname))
                key_namekey2 = goutcome.get_key_namekey((prefix, mod,
                                                         testname))
                assert key_namekey1 == key_namekey2



        goutcome_top = summary.GatherOutcomeSet({'sub': goutcome})

        assert goutcome_top.failed == set([('sub', 'foo', 'a.b', 'test_one')])

        assert goutcome_top.numpassed == 3

        res = goutcome_top.get_outcome(('sub', 'foo', 'a.b', 'test_one'))
        assert res == 'F'

        res = goutcome_top.get_key_namekey(('sub', 'foo', 'a.b', 'test_one'))
        assert res == (key_foo, ('a.b', 'test_one'))

        res = goutcome_top.get_longrepr(('sub', 'foo', 'a.b', 'test_one'))
        assert res == "some\ntraceback\n"

        # absent
        res = goutcome_top.get_outcome(('what', 'foo', 'a.b', 'test_one'))
        assert res == ' '

        res = goutcome_top.get_longrepr(('what', 'foo', 'a.b', 'test_one'))
        assert res == ''        

def test_colsizes():
    failed = [('a', 'abc', 'd'), ('ab', 'c', 'xy'),
              ('ab', '', 'cd')]
    
    res = summary.colsizes(failed)
    
    assert res == [2,3,2]

def test__prune_runs():
    runs = dict(zip(range(100), range(100, 200)))

    summary.Summary._prune_runs(runs, 4)

    assert len(runs) == 4

    assert runs == {99: 199, 98: 198, 97: 197, 96: 196}

def test_show_elapsed():
    res = summary.show_elapsed(0.25)
    assert res == "0.25s"
    res = summary.show_elapsed(1.0)
    assert res == "1.00s"           
    res = summary.show_elapsed(1.25)
    assert res == "1.25s"   
    res = summary.show_elapsed(4.5)
    assert res == "4.50s"
    res = summary.show_elapsed(5.25)
    assert res == "5s"
    res = summary.show_elapsed(5.5)
    assert res == "6s"            
    res = summary.show_elapsed(2*60+30)
    assert res == "2m30"
    res = summary.show_elapsed(4*60+30)
    assert res == "4m30"
    res = summary.show_elapsed(5*60+30)
    assert res == "6m"
    res = summary.show_elapsed(61*60)
    assert res == "1h1"
    res = summary.show_elapsed(90*60)
    assert res == "1h30"                

def _BuilderToStatus(status):

    setup = {'name': 'builder', 'builddir': 'BUILDDIR',
             'factory': process_factory.BuildFactory() }
    return process_builder.Builder(setup, status)

class FakeRequest(object):

    def __init__(self, builders, args={}):
        status = status_builder.Status(self, '/tmp')
        status.basedir = None
        self.status = status
        self.args = args

        self.builderNames = []
        self.builders = {}
        for builder in builders:
            name = builder.getName()
            self.builderNames.append(name)
            self.builders[name] = _BuilderToStatus(builder)

        self.site = self
        self.buildbot_service = self
        self.parent = self
        self.buildbotURL = "http://buildbot/"

    def getStatus(self):
        return self.status

def witness_branches(summary):
    ref = [None]
    recentRuns = summary.recentRuns
    def witness(*args, **kwds):
        branches = recentRuns(*args, **kwds)
        ref[0] = branches
        return branches
    summary.recentRuns = witness

    return lambda: ref[0]

class FakeLog(object):
    implements(buildbot_intefaces.IStatusLog)

    def __init__(self, step, name, cont=""):
        self.step = step
        self.name = name
        self.cont = cont
        
    def getStep(self):
        return self.step

    def getName(self):
        return self.name

    def hasContents(self):
        return True

    def readlines(self):
        return [l+'\n' for l in self.cont.splitlines()]

def add_builds(builder, builds):
    n = getattr(builder, 'nextBuildNumber', 0)
    t = 1000
    for rev, reslog in builds:
        build = status_builder.BuildStatus(builder, n)
        build.setProperty('got_revision', str(rev), None)
        step = build.addStepWithName('pytest')
        step.logs.extend([FakeLog(step, 'pytestLog', reslog),
                          FakeLog(step, 'stdio')])
        step.started = t
        step.finished = t + (n+1)*60
        t = step.finished + 30
        build.buildFinished()
        builder.addBuildToCache(build)
        n += 1
    builder.nextBuildNumber = n
        

class TestSummary(object):

    def setup_method(self, meth):
        summary.outcome_set_cache.clear()

    def test_sanity(self):
        s = summary.Summary()
        res = witness_branches(s)
        req = FakeRequest([])
        s.body(req)
        branches = res()

        assert branches == {}

    def test_one_build_no_rev(self):
        builder = status_builder.BuilderStatus('builder0')
        build = status_builder.BuildStatus(builder, 0)
        build.buildFinished()
        builder.addBuildToCache(build)
        builder.nextBuildNumber = len(builder.buildCache)

        s = summary.Summary()
        res = witness_branches(s)        
        req = FakeRequest([builder])
        out = s.body(req)
        branches = res()

        assert branches == {None: ({}, [build])}

    def test_one_build_no_logs(self):
        builder = status_builder.BuilderStatus('builder0')
        build = status_builder.BuildStatus(builder, 0)
        build.setProperty('got_revision', '50000', None)
        build.buildFinished()
        builder.addBuildToCache(build)
        builder.nextBuildNumber = len(builder.buildCache)

        s = summary.Summary()
        res = witness_branches(s)        
        req = FakeRequest([builder])
        out = s.body(req)
        branches = res()
        
        revs = branches[None][0]
        assert revs.keys() == [50000]

        assert '&lt;run&gt;' in out

    def test_one_build_no_logs_failure(self):
        builder = status_builder.BuilderStatus('builder0')
        build = status_builder.BuildStatus(builder, 0)
        build.setProperty('got_revision', '50000', None)
        step = build.addStepWithName('step')
        step.setText(['step', 'borken'])
        step.stepFinished(summary.FAILURE)
        step1 = build.addStepWithName('other')
        step1.setText(['other', 'borken'])
        step1.stepFinished(summary.FAILURE)        
        build.buildFinished()
        builder.addBuildToCache(build)
        builder.nextBuildNumber = len(builder.buildCache)

        s = summary.Summary()
        res = witness_branches(s)        
        req = FakeRequest([builder])
        out = s.body(req)
        branches = res()
        
        revs = branches[None][0]
        assert revs.keys() == [50000]

        assert 'step borken' in out
        assert 'other borken' not in out        
        
    def test_one_build(self):
        builder = status_builder.BuilderStatus('builder0')
        add_builds(builder, [(60000, "F TEST1\n. b")])

        s = summary.Summary()
        res = witness_branches(s)        
        req = FakeRequest([builder])
        out = s.body(req)
        branches = res()

        revs = branches[None][0]
        assert revs.keys() == [60000]
        outcome = revs[60000]['builder0']
        assert outcome.revision == 60000
        assert outcome.key == ('builder0', 0)

        assert 'TEST1' in out

    def test_two_builds(self):
        builder = status_builder.BuilderStatus('builder0')
        add_builds(builder, [(60000, "F TEST1\n. b"),
                             (60001, "F TEST1\n. b")])

        s = summary.Summary()
        res = witness_branches(s)        
        req = FakeRequest([builder])
        out = s.body(req)
        branches = res()

        revs = branches[None][0]
        assert sorted(revs.keys()) == [60000, 60001]        
        outcome = revs[60000]['builder0']
        assert outcome.revision == 60000
        assert outcome.key == ('builder0', 0)
        outcome = revs[60001]['builder0']
        assert outcome.revision == 60001
        assert outcome.key == ('builder0', 1)

        revs = []
        for m in re.finditer(r'recentrev=(\d+)', out):
            revs.append(int(m.group(1)))

        assert revs == [60000, 60001]

        assert 'TEST1' in out        

    def test_two_builds_samerev(self):
        builder = status_builder.BuilderStatus('builder0')
        add_builds(builder, [(60000, "F TEST1\n. b"),
                             (60000, "F TEST1\n. b")])        

        s = summary.Summary()
        res = witness_branches(s)        
        req = FakeRequest([builder])
        out = s.body(req)
        branches = res()

        revs = branches[None][0]
        assert sorted(revs.keys()) == [60000]
        outcome = revs[60000]['builder0']
        assert outcome.revision == 60000
        assert outcome.key == ('builder0', 1)

        assert 'TEST1' in out

    def test_two_builds_recentrev(self):
        builder = status_builder.BuilderStatus('builder0')
        add_builds(builder, [(60000, "F TEST1\n. b"),
                             (60001, "F TEST1\n. b")])

        s = summary.Summary()
        res = witness_branches(s)        
        req = FakeRequest([builder])
        req.args = {'recentrev': ['60000']}
        out = s.body(req)
        branches = res()

        revs = branches[None][0]
        assert sorted(revs.keys()) == [60000]
        outcome = revs[60000]['builder0']
        assert outcome.revision == 60000
        assert outcome.key == ('builder0', 0)

        assert 'TEST1' in out

    def test_many_builds_query_builder(self):
        builder = status_builder.BuilderStatus('builder0')
        add_builds(builder, [(60000, "F TEST1\n. b"),
                             (60000, ". a\n. b"),
                             (60001, "F TEST1\n. b")])        

        s = summary.Summary()
        res = witness_branches(s)        
        req = FakeRequest([builder])
        req.args={'builder': ['builder0']}
        out = s.body(req)
        branches = res()

        runs = branches[None][0]
        assert sorted(runs.keys()) == [(60000,0), (60000,1), (60001,2)]
        outcome = runs[(60000,0)]['builder0']
        assert outcome.revision == 60000
        assert outcome.key == ('builder0', 0)
        outcome = runs[(60000,1)]['builder0']
        assert outcome.revision == 60000
        assert outcome.key == ('builder0', 1)
        outcome = runs[(60001,2)]['builder0']
        assert outcome.revision == 60001
        assert outcome.key == ('builder0', 2)

        runs = []
        for m in re.finditer(r'builder=(\w+)&amp;builds=(\d+)', out):
            runs.append((m.group(1), int(m.group(2))))

        assert runs == [('builder0', 0),
                        ('builder0', 1),
                        ('builder0', 2)]

        assert 'TEST1' in out


    def test_many_builds_query_builder_builds(self):
        builder = status_builder.BuilderStatus('builder0')
        add_builds(builder, [(60000, "F TEST1\n. b"),
                             (60000, ". a\n. b"),
                             (60001, "F TEST1\n. b")])        

        s = summary.Summary()
        res = witness_branches(s)        
        req = FakeRequest([builder])
        req.args={'builder': ['builder0'],
                  'builds': ['0','2-2', '7']}
        out = s.body(req)
        branches = res()

        runs = branches[None][0]
        assert sorted(runs.keys()) == [(60000,0), (60001,2)]
        outcome = runs[(60000,0)]['builder0']
        assert outcome.revision == 60000
        assert outcome.key == ('builder0', 0)
        outcome = runs[(60001,2)]['builder0']
        assert outcome.revision == 60001
        assert outcome.key == ('builder0', 2)

        runs = []
        for m in re.finditer(r'builder=(\w+)&amp;builds=(\d+)', out):
            runs.append((m.group(1), int(m.group(2))))

        assert runs == [('builder0', 0),
                        ('builder0', 2)]

        assert 'TEST1' in out

    def test_many_pytestLogs(self):
        builder = status_builder.BuilderStatus('builder1')
        build = status_builder.BuildStatus(builder, 0)
        build.setProperty('got_revision', '70000', None)
        step = build.addStepWithName('pytest')
        step.logs.extend([FakeLog(step, 'pytestLog', "F TEST1")])
        step2 = build.addStepWithName('pytest2')
        step2.logs.extend([FakeLog(step, 'pytestLog', ". x\nF TEST2")])
        step2.setText(["pytest2", "aborted"])
        build.buildFinished()
        builder.addBuildToCache(build)
        builder.nextBuildNumber = 1

        s = summary.Summary()
        req = FakeRequest([builder])
        out = s.body(req)

        assert 'TEST1' in out
        assert 'TEST2' in out
        assert 'pytest aborted' not in out        
        assert 'pytest2 aborted' in out
