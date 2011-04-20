#XXX imports in conftest globals dont sow in coverage reports


def pytest_funcarg__mails(request):
    return []


def pytest_funcarg__messages(request):
    return []


def pytest_runtest_setup(item):
    from bitbucket_hook import hook
    hook.seen_nodes.clear()


def pytest_funcarg__monkeypatch(request):
    from bitbucket_hook import irc, mail
    mp = request.getfuncargvalue('monkeypatch')
    mails = request.getfuncargvalue('mails')

    def send(from_, to, subject, body, test=False, mails=mails):
        mails.append((from_, to, subject, body))
    mp.setattr(mail, 'send', send)

    messages = request.getfuncargvalue('messages')

    def send_irc_message(message, test=False):
        messages.append(message)
    mp.setattr(irc, 'send_message', send_irc_message)

    return mp
