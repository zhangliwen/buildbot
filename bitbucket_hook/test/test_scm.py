# -*- encoding: utf-8 -*-
from bitbucket_hook import scm


def test_non_ascii_encoding_guess_utf8(monkeypatch):
    def _hgexe(argv):
        return u'späm'.encode('utf-8'), '', 0
    monkeypatch.setattr(scm, '_hgexe', _hgexe)
    stdout = scm.hg('foobar')
    assert type(stdout) is unicode
    assert stdout == u'späm'


def test_non_ascii_encoding_invalid_utf8(monkeypatch):
    def _hgexe(argv):
        return '\xe4aa', '', 0 # invalid utf-8 string
    monkeypatch.setattr(scm, '_hgexe', _hgexe)
    stdout = scm.hg('foobar')
    assert type(stdout) is unicode
    assert stdout == u'\ufffdaa'

