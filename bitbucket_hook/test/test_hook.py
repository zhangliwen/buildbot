# -*- encoding: utf-8 -*-
import py
import pytest
from bitbucket_hook import hook, scm, mail, irc

#XXX
hook.app.config['USE_COLOR_CODES'] = False


def test_sort_commits():
    #
    commits = hook.get_commits('test_sort', {
        'commits': [
            {'revision': 43, 'node': 'second', 'raw_node': 'first'},
            {'revision': 42, 'node': 'first', 'raw_node': 'second'},
        ],
    })
    commits = [x['node'] for x in commits]

    assert commits == ['first', 'second']


LONG_MESSAGE = u'This is a test with a long message: ' + 'x' * 1000
LONG_CUT = LONG_MESSAGE[:160 - 29]


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

    cases = [(no_file,  ''),  # No diff
             (single_file, 'single'),  # Single file
             (multiple_files,   ''),  # No common prefix
             (multiple_files_subdir, 'path/'),  # Common prefix
             (multiple_files_subdir_root, ''),  # No common subdir file in root
             (single_file_deep, 'path/to/single'),  # Single file in deep path
            ]

    author = u'antocuni'
    branch = u'mybranch'

    expected_template = '%s %s %%s /%%s: %%s...' % (author, branch)
    expected = []
    commits = payload['commits']

    for i, (case, snippet) in enumerate(cases):
        rev = 44 + i
        node = chr(97 + i) + 'xxyyy'
        raw_node = node * 2
        expected.append(expected_template % (node, snippet, LONG_CUT))
        commits.append(d(revision=rev, files=case, author=author,
                         branch=branch, message=LONG_MESSAGE, node=node,
                         raw_node=raw_node))

    return payload, expected


def test_irc_message(monkeypatch, messages):
    payload = {
        'commits': [
            {
                'revision': 42,
                'branch': u'default',
                'author': u'antocuni',
                'message': u'this is a test',
                'node': 'abcdef',
                'raw_node': 'abcdef',
            },
            {
                'revision': 43,
                'author': u'antocuni',
                'branch': u'mybranch',
                'message': LONG_MESSAGE,
                'node': 'xxxyyy',
                'raw_node': 'xxxyyy',
            },
        ]
    }

    payload, expected = irc_cases(payload)
    irc.handle_message(payload)

    msg1, msg2 = messages[:2]

    assert msg1 == 'antocuni default abcdef /: this is a test'
    x = 'antocuni mybranch xxxyyy /: %s...' % LONG_CUT
    assert msg2 == x

    for got, wanted in zip(messages[2:], expected):
        assert got == wanted


def noop(*args, **kwargs):
    pass


class mock:
    __init__ = noop

    def communicate(*args, **kwargs):
        return '1', 2

    def wait(*args, **kwargs):
        return 0

    sendmail = noop


def test_handle(monkeypatch):
    commits, _ = irc_cases()
    test_payload = {u'repository': {u'absolute_url': '',
                                    u'name': u'test',
                                    u'owner': u'antocuni',
                                    u'slug': u'test',
                                    u'website': u''},
                    u'user': u'antocuni',
                    'commits': commits['commits']}

    monkeypatch.setattr(scm, 'Popen', mock)
    monkeypatch.setattr(irc.subprocess, 'call', noop)
    monkeypatch.setattr(mail, 'SMTP', mock)

    hook.handle(test_payload)
    hook.handle(test_payload, test=True)

    hook.app.config['LISTFILES'] = True
    hook.handle(test_payload)
    hook.handle(test_payload, test=True)


def test_handle_unknown(monkeypatch):
    def hgraise(*k):
        raise Exception('this should never be called')

    py.test.raises(Exception, hgraise)

    monkeypatch.setattr(scm, 'hg', hgraise)
    hook.handle({
        u'repository': {
            u'absolute_url': 'uhm/missing/yeah',
        },
    })


def test_ignore_duplicate_commits(monkeypatch, mails, messages):
    monkeypatch.setattr(hook, 'seen_nodes', set())

    commits, _ = irc_cases()
    payload = {u'repository': {u'absolute_url': '',
                               u'name': u'test',
                               u'owner': u'antocuni',
                               u'slug': u'test',
                               u'website': u''},
               u'user': u'antocuni',
               'commits': commits['commits']}
    commits_listed = list(hook.get_commits('test', payload))
    commits_again = list(hook.get_commits('test', payload))
    num_commits = len(commits['commits'])
    assert len(commits_listed) == num_commits
    assert not commits_again

