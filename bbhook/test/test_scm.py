# -*- encoding: utf-8 -*-
import py
import pytest

from bbhook import scm


def test_non_ascii_encoding_guess_utf8(monkeypatch):

    def _hgexe(argv):
        return u'späm'.encode('utf-8'), '', 0
    monkeypatch.setattr(scm, '_hgexe', _hgexe)
    stdout = scm.hg('foobar')
    assert type(stdout) is unicode
    assert stdout == u'späm'


def test_non_ascii_encoding_invalid_utf8(monkeypatch):

    def _hgexe(argv):
        return '\xe4aa', '', 0  # invalid utf-8 string
    monkeypatch.setattr(scm, '_hgexe', _hgexe)
    stdout = scm.hg('foobar')
    assert type(stdout) is unicode
    assert stdout == u'\ufffdaa'


@pytest.mark.skip_if("not py.path.local.sysfind('hg')",
                     reason='hg binary missing')
def test_hg():
    scm.hg('help')
    with pytest.raises(Exception):
        print scm.hg
        scm.hg('uhmwrong')


def test_huge_diff(monkeypatch):
    monkeypatch.setattr(scm, 'MAX_DIFF_LINES', 4)
    lines = """\
one
two
three
for
five
six
""".splitlines(True)
    diff = scm.filter_diff(lines)
    assert diff == """\
diff too long, truncating to 4 out of 6 lines

one
two
three
for
"""
