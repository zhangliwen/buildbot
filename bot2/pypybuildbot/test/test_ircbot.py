from pypybuildbot import ircbot

def setup_module(mod):
    ircbot.USE_COLOR_CODES = False

def teardown_module(mod):
    ircbot.USE_COLOR_CODES = True

class FakeBuild(object):

    def __init__(self, reason=None, source=None):
        self.reason = reason
        self.source = source

    def getReason(self):
        return self.reason

    def getSourceStamp(self):
        return self.source

class FakeSource(object):

    def __init__(self, branch):
        self.branch = branch

def test_extract_username():
    a = FakeBuild("The web-page 'force build' button was pressed by 'antocuni': foo")
    b = FakeBuild("The web-page 'force build' button was ...")
    assert ircbot.extract_username(a) == 'antocuni'
    assert ircbot.extract_username(b) is None


def test_get_description_for_build():
    a = FakeBuild('foobar', source=FakeSource(None))
    msg = ircbot.get_description_for_build("http://myurl", a)
    assert msg == "http://myurl"

    a = FakeBuild("The web-page 'force build' button was pressed by 'antocuni': foo",
                  source=FakeSource(None))
    msg = ircbot.get_description_for_build("http://myurl", a)
    assert msg == "http://myurl [antocuni]"

    a = FakeBuild('foobar', source=FakeSource('mybranch'))
    msg = ircbot.get_description_for_build("http://myurl", a)
    assert msg == "http://myurl [mybranch]"

    a = FakeBuild("The web-page 'force build' button was pressed by 'antocuni': foo",
                  source=FakeSource('mybranch'))
    msg = ircbot.get_description_for_build("http://myurl", a)
    assert msg == "http://myurl [antocuni, mybranch]"
