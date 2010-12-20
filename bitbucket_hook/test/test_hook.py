# -*- encoding: utf-8 -*-

from bitbucket_hook.hook import BitbucketHookHandler

class BaseHandler(BitbucketHookHandler):

    def __init__(self):
        self.mails = []

    def send(self, from_, to, subject, body):
        self.mails.append((from_, to, subject, body))
    

def test_non_ascii_encoding_guess_utf8():
    class MyHandler(BaseHandler):
        def _hgexe(self, argv):
            return u'späm'.encode('utf-8'), '', 0
    #
    handler = MyHandler()
    stdout = handler.hg('foobar')
    assert type(stdout) is unicode
    assert stdout == u'späm'

def test_non_ascii_encoding_invalid_utf8():
    class MyHandler(BaseHandler):
        def _hgexe(self, argv):
            return '\xe4aa', '', 0 # invalid utf-8 string
    #
    handler = MyHandler()
    stdout = handler.hg('foobar')
    assert type(stdout) is unicode
    assert stdout == u'\ufffdaa'
