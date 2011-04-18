# -*- encoding: utf-8 -*-

from bitbucket_hook import hook

class BaseHandler(hook.BitbucketHookHandler):

    USE_COLOR_CODES = False

    def __init__(self):
        hook.BitbucketHookHandler.__init__(self)
        self.mails = []
        self.messages = []

    def send(self, from_, to, subject, body, test=False):
        self.mails.append((from_, to, subject, body))

    def send_irc_message(self, message, test=False):
        self.messages.append(message)


def test_non_ascii_encoding_guess_utf8(monkeypatch):
    def _hgexe(argv):
        return u'späm'.encode('utf-8'), '', 0
    monkeypatch.setattr(hook, '_hgexe', _hgexe)
    stdout = hook.hg('foobar')
    assert type(stdout) is unicode
    assert stdout == u'späm'

def test_non_ascii_encoding_invalid_utf8(monkeypatch):
    def _hgexe(argv):
        return '\xe4aa', '', 0 # invalid utf-8 string
    #
    monkeypatch.setattr(hook, '_hgexe', _hgexe)
    stdout = hook.hg('foobar')
    assert type(stdout) is unicode
    assert stdout == u'\ufffdaa'

def test_sort_commits():
    class MyHandler(BaseHandler):
        def __init__(self):
            BaseHandler.__init__(self)
            self.sent_commits = []
        def send_diff_for_commit(self, commit, test=False):
            self.sent_commits.append(commit['node'])
    #
    handler = MyHandler()
    handler.payload = {
        'commits': [{'revision': 43, 'node': 'second', 'raw_node': 'first'},
                    {'revision': 42, 'node': 'first', 'raw_node': 'second'}]
        }
    handler.handle_diff_email()
    assert handler.sent_commits == ['first', 'second']

def test_getpaths():
    d = dict

    barefile = [d(file='file')]
    distinct = [d(file='path1/file1'), d(file='path2/file2'),
                d(file='path3/file')]
    shared = [d(file='path/file1'), d(file='path/file2'),
              d(file='path/file')]

    deepfile = [d(file='a/long/path/to/deepfile.py')]
    slashesfile = [d(file='/slashesfile/')]
    slashleft = [d(file='/slashleft')]
    slashright = [d(file='slashright/')]


    nocommon = distinct + [d(file='path4/file')]
    nocommonplusroot = distinct + barefile

    common = [d(file='some/path/to/file'), d(file='some/path/to/deeper/file'),
              d(file='some/path/to/anotherfile'), d(file='some/path/to/afile')]
    commonplusroot = shared + barefile

    empty = d(file='')
    nocommonplusempty = distinct + [empty]
    commonplusempty = shared + [empty]
    nocommonplusslash = distinct + [d(file='path4/dir/')]
    commonplusslash = shared + [d(file='path/dir/')]

    pypydoubleslash = [d(file='pypy/jit/metainterp/opt/u.py'),
                       d(file='pypy/jit/metainterp/test/test_c.py'),
                       d(file='pypy/jit/metainterp/test/test_o.py')]

    pypyempty = [d(file='pypy/rlib/rdtoa.py'),
                 d(file='pypy/rlib/test/test_rdtoa.py')]

    nothing = ('', '')

    # (input, expected output) for listfiles=False
    files_expected = [([], nothing),
                      ([empty], nothing),
                      ([empty, empty], nothing),
                      (barefile, ('file', '')),
                      (deepfile, ('a/long/path/to/deepfile.py', '')),
                      (slashesfile, ('/slashesfile/', '')),
                      (slashleft, ('/slashleft', '')),
                      (slashright, ('slashright/', '')),
                      (nocommon, nothing),
                      (nocommonplusroot, nothing),
                      (nocommonplusempty, nothing),
                      (common, ('some/path/to/', '')),
                      (commonplusroot, nothing),
                      (commonplusempty, nothing),
                      (nocommonplusslash, nothing),
                      (commonplusslash, ('path/', '')),
                      (pypydoubleslash, ('pypy/jit/metainterp/', '')),
                      (pypyempty, ('pypy/rlib/', '')),
                      ]

    for f, wanted in files_expected:
        assert hook.getpaths(f) == wanted

    # (input, expected output) for listfiles=True
    files_expected = [([], nothing),
                      ([empty], nothing),
                      ([empty, empty], nothing),
                      (barefile, ('file', '')),
                      (deepfile, ('a/long/path/to/deepfile.py', '')),
                      (slashesfile, ('/slashesfile/', '')),
                      (slashleft, ('/slashleft', '')),
                      (slashright, ('slashright/', '')),
                      (nocommon, ('', ' M(file1, file2, file, file)')),
                      (nocommonplusroot, ('', ' M(file1, file2, file, file)')),
                      (nocommonplusempty, ('',' M(file1, file2, file)')),
                      (common, ('some/path/to/',
                                ' M(file, file, anotherfile, afile)')),
                      (commonplusroot, ('', ' M(file1, file2, file, file)')),
                      (commonplusempty, ('',' M(file1, file2, file)')),
                      (nocommonplusslash, ('',' M(file1, file2, file)')),
                      (commonplusslash, ('path/',' M(file1, file2, file)')),
                      (pypydoubleslash, ('pypy/jit/metainterp/',
                                         ' M(u.py, test_c.py, test_o.py)')),
                      (pypyempty, ('pypy/rlib/',
                                   ' M(rdtoa.py, test_rdtoa.py)')),
                      ]

    for f, wanted in files_expected:
        assert hook.getpaths(f, listfiles=True) == wanted



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

    cases = [(no_file,  ''), # No diff
             (single_file,'single'), # Single file
             (multiple_files,   ''),  # No common prefix
             (multiple_files_subdir, 'path/'), # Common prefix
             (multiple_files_subdir_root, ''), # No common subdir, file in root
             (single_file_deep,'path/to/single') # Single file in deep path
            ]

    author = u'antocuni'
    branch = u'mybranch'

    expected_template = '%s %s %%s /%%s: %%s...' % (author, branch)
    expected = []
    commits = payload['commits']

    for i, (case, snippet) in enumerate(cases):
        rev = 44 + i
        node = chr(97+i) + 'xxyyy'
        raw_node = node * 2
        expected.append(expected_template % (node, snippet, LONG_CUT))
        commits.append(d(revision=rev, files=case, author=author,
                         branch=branch, message=LONG_MESSAGE, node=node,
                         raw_node=raw_node))

    return payload, expected


def test_irc_message():
    handler = BaseHandler()
    handler.payload = {
        'commits': [{'revision': 42,
                     'branch': u'default',
                     'author': u'antocuni',
                     'message': u'this is a test',
                     'node': 'abcdef',
                     'raw_node': 'abcdef',
                     },
                    {'revision': 43,
                     'author': u'antocuni',
                     'branch': u'mybranch',
                     'message': LONG_MESSAGE,
                     'node': 'xxxyyy',
                     'raw_node': 'xxxyyy',
                     }
                    ]}

    handler.payload, expected = irc_cases(handler.payload)
    handler.handle_irc_message()

    msg1, msg2 = handler.messages[:2]

    assert msg1 == 'antocuni default abcdef /: this is a test'
    x = 'antocuni mybranch xxxyyy /: %s...' % LONG_CUT
    assert msg2 == x

    for got, wanted in zip(handler.messages[2:], expected):
        assert got == wanted

def noop(*args, **kwargs): pass
class mock:
    __init__ = noop
    def communicate(*args, **kwargs): return '1', 2
    def wait(*args, **kwargs): return 0
    sendmail = noop

def test_handle(monkeypatch):
    handler = hook.BitbucketHookHandler()
    commits, _ = irc_cases()
    test_payload = {u'repository': {u'absolute_url': '',
                                    u'name': u'test',
                                    u'owner': u'antocuni',
                                    u'slug': u'test',
                                    u'website': u''},
                    u'user': u'antocuni',
                    'commits': commits['commits']}

    handler.call_subprocess = noop
    monkeypatch.setattr(hook, 'Popen', mock)
    handler.SMTP = mock

    handler.handle(test_payload)
    handler.handle(test_payload, test=True)

    handler.LISTFILES = True
    handler.handle(test_payload)
    handler.handle(test_payload, test=True)


def test_ignore_duplicate_commits(monkeypatch):
    def hg(self, *args):
        return '<hg %s>' % ' '.join(map(str, args))
    monkeypatch.setattr(hook, 'hg', hg)
    class MyHandler(BaseHandler):
        seen_nodes = set() # make sure we do not depend on what the other
                           # tests did
        
        def check_for_local_repo(self, local_repo):
            return True

    handler = MyHandler()
    commits, _ = irc_cases()
    payload = {u'repository': {u'absolute_url': '',
                               u'name': u'test',
                               u'owner': u'antocuni',
                               u'slug': u'test',
                               u'website': u''},
               u'user': u'antocuni',
               'commits': commits['commits']}
    handler.handle(payload)
    handler.handle(payload)
    #
    num_commits = len(commits['commits'])
    assert len(handler.mails) == num_commits
    assert len(handler.messages) == num_commits
