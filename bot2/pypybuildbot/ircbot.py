"""
Monkeypatch buildbot.status.words.Contact: this is the easiest (only?) way to
customize the messages sent by the IRC bot.  Tested with buildbot 0.8.4p2,
might break in future versions.

If you uncomment out this code, things will still work and you'll just loose
the customized IRC messages.
"""

from buildbot.status.words import IRC, log, IRCContact

# see http://www.mirc.com/colors.html
USE_COLOR_CODES = True
BOLD = '\x02'
COLORS = {
    'WHITE': '\x030',
    'BLACK': '\x031',
    'GREEN': '\x033',
    'RED': '\x034',
    'AZURE': '\x0311',
    'BLUE': '\x0312',
    'PURPLE': '\x0313',
    'GRAY': '\x0315',
}


def color(s, code=None, bold=False):
    if USE_COLOR_CODES:
        c = BOLD if bold else ''
        if code in COLORS:
            c += COLORS[code]
        return '%s%s\x0F' % (c, s)
    return s


def extract_username(build):
    owner = build.getProperty("owner")
    reason = build.getProperty("reason")
    return ": ".join(k for k in (owner, reason) if k)


def get_description_for_build(url, build):
    url = color(url, 'GRAY')  # in gray
    infos = []
    username = extract_username(build)
    if username:
        infos.append(color(username, 'BLUE'))  # in blue
    #
    branch = build.getProperty('branch')
    if branch:
        infos.append(color(branch, bold=True))  # in bold
    #
    if infos:
        return '%s [%s]' % (url, ', '.join(infos))
    else:
        return url


def buildStarted(self, builderName, build):
    builder = build.getBuilder()
    log.msg('[Contact] Builder %r in category %s started' %
                                            (builder, builder.category))

    # only notify about builders we are interested in

    if (self.bot.categories is not None and
       builder.category not in self.bot.categories):
        log.msg('Not notifying for a build in the wrong category')
        return

    if not self.notify_for('started'):
        log.msg('Not notifying for a build when started-notification disabled')
        return

    buildurl = self.bot.status.getURLForThing(build)
    descr = get_description_for_build(buildurl, build)
    msg = "Started: %s" % descr
    self.send(msg)


def buildFinished(self, builderName, build, results):
    builder = build.getBuilder()

    # only notify about builders we are interested in
    log.msg('[Contact] builder %r in category %s finished' %
                                            (builder, builder.category))

    if (self.bot.categories is not None and
        builder.category not in self.bot.categories):
        return

    if not self.notify_for_finished(build):
        return

    buildurl = self.bot.status.getURLForThing(build)
    descr = get_description_for_build(buildurl, build)
    result, c = self.results_descriptions.get(build.getResults(),
                                                ("Finished ??", 'RED'))
    if c not in COLORS:
        c = 'RED'
    result = color(result, c, bold=True)
    msg = "%s: %s" % (result, descr)
    self.send(msg)

IRCContact.buildStarted = buildStarted
IRCContact.buildFinished = buildFinished


## def send_message(message, test=False):
##     import subprocess
##     return subprocess.call([
##             '/tmp/commit-bot/message',
##             '#buildbot-test',
##             message])
## send_message(color(BOLD+PURPLE, 'ciao'))
