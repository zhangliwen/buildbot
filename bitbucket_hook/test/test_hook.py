# -*- encoding: utf-8 -*-

from bitbucket_hook.hook import BitbucketHookHandler

class BaseHandler(BitbucketHookHandler):

    def __init__(self):
        self.mails = []

    def send(self, from_, to, subject, body, test=False):
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
        def send_diff_for_commit(self, commit, test=False):
            self.sent_commits.append(commit['node'])
    #
    handler = MyHandler()
    handler.payload = {
        'commits': [{'revision': 43, 'node': 'second'},
                    {'revision': 42, 'node': 'first'}]
        }
    handler.handle_diff_email()
    assert handler.sent_commits == ['first', 'second']

def test_irc_message():
    LONG_MESSAGE = u'This is a test with a long message: ' + 'x'*1000
    class MyHandler(BaseHandler):
        USE_COLOR_CODES = False
        def __init__(self):
            self.messages = []
        def send_irc_message(self, message, test=False):
            self.messages.append(message)
    handler = MyHandler()

    d = dict
    no_file = []
    single_file = [d(file='single')]
    multiple_files = [d(file='file1'), d(file='file2'), d(file='file3')]
    single_file_subdir = [d(file='my/path/to/single')]
    multiple_files_subdir = [d(file='path/file1'), d(file='path/file2'),
                             d(file='path/file3')]
    multiple_files_subdir_root = [d(file='file1'), d(file='my/path/file2'),
                                  d(file='my/file3')]
    single_file_deep = [d(file='path/to/single')]

    handler.payload = {
        'commits': [{'revision': 42,
                     'branch': u'default',
                     'author': u'antocuni',
                     'message': u'this is a test',
                     'node': 'abcdef'
                     },
                    {'revision': 43,
                     'author': u'antocuni',
                     'branch': u'mybranch',
                     'message': LONG_MESSAGE,
                     'node': 'xxxyyy'
                     },
                    {'revision': 44,
                     'files': no_file,
                     'author': u'antocuni',
                     'branch': u'mybranch',
                     'message': LONG_MESSAGE,
                     'node': 'axxyyy'
                     },
                    {'revision': 45,
                     'author': u'antocuni',
                     'files': single_file,
                     'branch': u'mybranch',
                     'message': LONG_MESSAGE,
                     'node': 'bxxyyy'
                     },
                    {'revision': 46,
                     'author': u'antocuni',
                     'files': multiple_files,
                     'branch': u'mybranch',
                     'message': LONG_MESSAGE,
                     'node': 'cxxyyy'
                     },
                    {'revision': 47,
                     'author': u'antocuni',
                     'files': multiple_files_subdir,
                     'branch': u'mybranch',
                     'message': LONG_MESSAGE,
                     'node': 'dxxyyy'
                     },
                    {'revision': 48,
                     'author': u'antocuni',
                     'files': multiple_files_subdir_root,
                     'branch': u'mybranch',
                     'message': LONG_MESSAGE,
                     'node': 'exxyyy'
                     },
                    {'revision': 49,
                     'author': u'antocuni',
                     'files': single_file_deep,
                     'branch': u'mybranch',
                     'message': LONG_MESSAGE,
                     'node': 'fxxyyy'
                     }
                    ]
        }
    handler.handle_irc_message()
    msg1, msg2, msg3, msg4, msg5, msg6, msg7, msg8 = handler.messages
    assert msg1 == 'antocuni default abcdef /: this is a test'
    x = 'antocuni mybranch xxxyyy /: %s...' % LONG_MESSAGE[:160-29]
    assert msg2 == x

    # No diff
    x = 'antocuni mybranch axxyyy /: %s...' % LONG_MESSAGE[:160-29]
    assert msg3 == x

    # Single file
    x = 'antocuni mybranch bxxyyy /single: %s...' % LONG_MESSAGE[:160-29]
    assert msg4 == x

    x = 'antocuni mybranch cxxyyy /: %s...' % LONG_MESSAGE[:160-29]
    assert msg5 == x
    x = 'antocuni mybranch dxxyyy /path/: %s...' % LONG_MESSAGE[:160-29]
    assert msg6 == x
    x = 'antocuni mybranch exxyyy /my/: %s...' % LONG_MESSAGE[:160-29]
    assert msg7 == x
    x = 'antocuni mybranch fxxyyy /path/to/single: %s...' % LONG_MESSAGE[:160-29]
    assert msg8 == x
