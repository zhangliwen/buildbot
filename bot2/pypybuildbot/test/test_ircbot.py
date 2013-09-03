from pypybuildbot import ircbot


def setup_module(mod):
    ircbot.USE_COLOR_CODES = False


def teardown_module(mod):
    ircbot.USE_COLOR_CODES = True


class FakeBuild(object):

    def __init__(self, reason=None, owner=None, branch=None):
        self.properties = {'owner': owner, 'branch': branch, 'reason': reason}

    def getProperty(self, name):
        return self.properties.get(name, None)


def test_get_build_information():
    a = FakeBuild(owner='antocuni',
            reason="The web-page 'force build' button was pressed")
    b = FakeBuild("The web-page 'force build' button was ...")
    assert ircbot.get_build_information(a) == \
            "antocuni: The web-page 'force build' button was pressed"
    assert ircbot.get_build_information(b) == \
            "The web-page 'force build' button was ..."


def test_get_description_for_build():
    a = FakeBuild()
    msg = ircbot.get_description_for_build("http://myurl", a)
    assert msg == "http://myurl"

    a = FakeBuild(owner='antocuni',
            reason="The web-page 'force build' button was pressed")
    msg = ircbot.get_description_for_build("http://myurl", a)
    assert msg == "http://myurl [antocuni: " \
                  + "The web-page 'force build' button was pressed]"

    a = FakeBuild(branch='mybranch')
    msg = ircbot.get_description_for_build("http://myurl", a)
    assert msg == "http://myurl [mybranch]"

    a = FakeBuild(owner='antocuni', branch='mybranch')
    msg = ircbot.get_description_for_build("http://myurl", a)
    assert msg == "http://myurl [antocuni, mybranch]"
