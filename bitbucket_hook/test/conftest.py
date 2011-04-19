from bitbucket_hook import hook

def pytest_funcarg__mails(request):
    return []


def pytest_funcarg__monkeypatch(request):
    mp =  request.getfuncargvalue('monkeypatch')
    mails = request.getfuncargvalue('mails')
    def send(from_, to, subject, body,test=False, mails=mails):
        mails.append((from_, to, subject, body))
    mp.setattr(hook, 'send', send)


    return mp

