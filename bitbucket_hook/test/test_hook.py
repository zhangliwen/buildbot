# -*- encoding: utf-8 -*-

from bitbucket_hook.hook import BitbucketHookHandler, getpaths

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

def test_getpaths():
    d = dict
    empty = d(file='')
    nothing = ('', '')

    barefile = [d(file='barefile')]
    slashesfile = [d(file='/slashesfile/')]
    slashleft = [d(file='/slashleft')]
    slashright = [d(file='/slashright')]
    nocommon = [d(file='path1/file'), d(file='path2/file'),
                d(file='path3/file'), d(file='path4/file')]

    files_expected = [([], nothing),
                      ([empty], nothing),
                      ([empty, empty], nothing),
                      (barefile, ('barefile', '')),
                      (slashesfile, ('/slashesfile/', '')),
                      (slashleft, ('/slashleft', '')),
                      (slashright, ('/slashright', '')),
                      (nocommon, nothing),
                      ]

    for f, wanted in files_expected:
        assert getpaths(f) == wanted


LONG_MESSAGE = u'This is a test with a long message: ' + 'x'*1000
LONG_CUT = LONG_MESSAGE[:160-29]

def irc_cases(payload=None):

    if payload is None:
        payload = {'commits': []}

    d = dict
    no_file = []
    single_file = [d(file='single')]
    multiple_files = [d(file='file1'), d(file='file2'), d(file='file3')]
    multiple_files_subdir = [d(file='path/file1'), d(file='path/file2'),
                             d(file='path/file3')]
    multiple_files_subdir_root = [d(file='file1'), d(file='my/path/file2'),
                                  d(file='my/file3')]
    single_file_deep = [d(file='path/to/single')]

    cases = (no_file, single_file, multiple_files,
             multiple_files_subdir, multiple_files_subdir_root,
             single_file_deep
            )

    expected = ['antocuni mybranch axxyyy /: %s...', # No diff
                'antocuni mybranch bxxyyy /single: %s...', # Single file
                'antocuni mybranch cxxyyy /: %s...',
                'antocuni mybranch dxxyyy /path/: %s...',
                'antocuni mybranch exxyyy /my/: %s...',
                'antocuni mybranch fxxyyy /path/to/single: %s...'
                ]

    commits = payload['commits']

    author = u'antocuni'
    branch = u'mybranch'

    for i, case in enumerate(cases):
        rev = 44 + i
        node = chr(97+i) + 'xxyyy'
        commits.append(d(revision=rev, files=case, author=author,
                         branch=branch, message=LONG_MESSAGE, node=node))

    return payload, expected


def test_irc_message():
    class MyHandler(BaseHandler):
        USE_COLOR_CODES = False
        def __init__(self):
            self.messages = []
        def send_irc_message(self, message, test=False):
            self.messages.append(message)

    handler = MyHandler()
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
                     }
                    ]}

    handler.payload, expected = irc_cases(handler.payload)
    handler.handle_irc_message()

    msg1, msg2 = handler.messages[:2]

    assert msg1 == 'antocuni default abcdef /: this is a test'
    x = 'antocuni mybranch xxxyyy /: %s...' % LONG_CUT
    assert msg2 == x

    for got, wanted in zip(handler.messages[2:], expected):
        wanted = wanted % LONG_CUT
        assert got == wanted
