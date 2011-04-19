from bitbucket_hook import hook

def pytest_funcarg__mails(request):
    return []

def pytest_funcarg__messages(request):
    return []

def pytest_funcarg__monkeypatch(request):
    mp =  request.getfuncargvalue('monkeypatch')
    mails = request.getfuncargvalue('mails')
    def send(from_, to, subject, body,test=False, mails=mails):
        mails.append((from_, to, subject, body))
    mp.setattr(hook, 'send', send)

    messages = request.getfuncargvalue('messages')
    def send_irc_message(message, test=False):
        messages.append(message)
    mp.setattr(hook, 'send_irc_message', send_irc_message)


    return mp

