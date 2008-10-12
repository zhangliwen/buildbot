from pypybuildbot import summary
from StringIO import StringIO

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
        cache = summary.RevisionOutcomeSetCache()
        cache.CACHESIZE = 3
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

def test__prune_revs():
    revs = dict(zip(range(100), range(100, 200)))

    summary.Summary._prune_revs(revs, 4)

    assert len(revs) == 4

    assert revs == {99: 199, 98: 198, 97: 197, 96: 196}
    

