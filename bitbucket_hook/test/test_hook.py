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

def test_sort_commits():
    class MyHandler(BaseHandler):
        def __init__(self):
            self.sent_commits = []
        def send_diff_for_commit(self, commit):
            self.sent_commits.append(commit['node'])

    #
    handler = MyHandler()
    handler.payload = {
        'commits': [{'revision': 43, 'node': 'second'},
                    {'revision': 42, 'node': 'first'}]
        }
    handler.handle_diff_email()
    assert handler.sent_commits == ['first', 'second']
