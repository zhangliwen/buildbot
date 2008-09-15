from pypybuildbot import summary
from StringIO import StringIO

class TestOutcomes(object):

    def test_populate(self):
        rev_outcome = summary.RevOutcome(50000)
        log = StringIO("""F a/b.py:test_one
. a/b.py:test_two
s a/b.py:test_three
""")
        
        rev_outcome.populate(log)

        assert rev_outcome.skipped == set([("a.b","test_three")])
        assert rev_outcome.failed == set([("a.b", "test_one")])

        res = rev_outcome.get_outcome(("a.b", "test_one"))
        assert res == 'F'

        res = rev_outcome.get_outcome(("a.b", "test_three"))
        assert res == 's'

        res = rev_outcome.get_outcome(("a.b", "test_two"))
        assert res == '.'


    def test_GatherOutcome(self):
        rev_outcome_foo = summary.RevOutcome(50000)
        log = StringIO("""F a/b.py:test_one
. a/b.py:test_two
s a/b.py:test_three
""")
        
        rev_outcome_foo.populate(log)

        
        rev_outcome_bar = summary.RevOutcome(50000)
        log = StringIO(""". a/b.py:test_one
. a/b.py:test_two
s a/b.py:test_three
""")
        
        rev_outcome_bar.populate(log)

        d = {'foo': rev_outcome_foo,
             'bar': rev_outcome_bar}

        goutcome = summary.GatherOutcome(d)

        
        assert goutcome.failed == set([('foo', 'a.b', 'test_one')])
        assert goutcome.failed == set([('foo', 'a.b', 'test_one')])

        assert goutcome.skipped == set([('foo', 'a.b', 'test_three'),
                                        ('bar', 'a.b', 'test_three'),
                                        ])
        assert goutcome.skipped == set([('foo', 'a.b', 'test_three'),
                                        ('bar', 'a.b', 'test_three'),
                                        ])

        for prefix in ('foo', 'bar'):
            for mod, testname in (("a.b", "test_one"), ("a.b", "test_two"),
                                  ("a.b", "test_three")):

                outcome1 = d[prefix].get_outcome((mod, testname))
                outcome2 = goutcome.get_outcome((prefix, mod, testname))
                assert outcome2 == outcome1

        goutcome_top = summary.GatherOutcome({'sub': goutcome})

        assert goutcome_top.failed == set([('sub', 'foo', 'a.b', 'test_one')])

        res = goutcome_top.get_outcome(('sub', 'foo', 'a.b', 'test_one'))
        assert res == 'F'
