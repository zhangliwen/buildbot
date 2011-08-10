"""
Monkeypatch buildbot.status.words.Contact: this is the easiest (only?) way to
customize the messages sent by the IRC bot.  Tested with buildbot 0.8.4p2,
might break in future versions.

If you uncomment out this code, things will still work and you'll just loose
the customized IRC messages.
"""

import re
from buildbot.status.words import Contact, IRC, log

USE_COLOR_CODES = True
GREEN  = '\x033'
RED    = '\x034'
AZURE  = '\x0311'
BLUE   = '\x0312'
PURPLE = '\x0313'
GRAY   = '\x0315'
BOLD   = '\x02'
def color(code, s):
    if USE_COLOR_CODES:
        return '%s%s\x0F' % (code, s)
    return s

def extract_username(build):
    regexp = r"The web-page 'force build' button was pressed by '(.*)': .*"
    match = re.match(regexp, build.getReason())
    if match:
        return match.group(1)
    return None


def get_description_for_build(url, build):
    url = color(GRAY, url) # in gray
    infos = []
    username = extract_username(build)
    if username:
        infos.append(color(BLUE, username)) # in blue
    #
    branch = build.source.branch
    if branch:
        infos.append(color(BOLD, branch)) # in bold
    #
    if infos:
        return '%s [%s]' % (url, ', '.join(infos))
    else:
        return url

def buildStarted(self, builderName, build):
    builder = build.getBuilder()
    log.msg('[Contact] Builder %r in category %s started' % (builder, builder.category))

    # only notify about builders we are interested in

    if (self.channel.categories != None and
       builder.category not in self.channel.categories):
        log.msg('Not notifying for a build in the wrong category')
        return

    if not self.notify_for('started'):
        log.msg('Not notifying for a build when started-notification disabled')
        return

    buildurl = self.channel.status.getURLForThing(build)
    descr = get_description_for_build(buildurl, build)
    msg = "Started: %s" % descr
    self.send(msg)


def buildFinished(self, builderName, build, results):
    builder = build.getBuilder()

    # only notify about builders we are interested in
    log.msg('[Contact] builder %r in category %s finished' % (builder, builder.category))

    if (self.channel.categories != None and
        builder.category not in self.channel.categories):
        return

    if not self.notify_for_finished(build):
        return

    buildurl = self.channel.status.getURLForThing(build)
    descr = get_description_for_build(buildurl, build)
    result = self.results_descriptions.get(build.getResults(), "Finished ??")
    if result == 'Success':
        result = color(BOLD+GREEN, result)
    elif result == 'Exception':
        result = color(BOLD+PURPLE, result)
    else:
        result = color(BOLD+RED, result)
    msg = "%s: %s" % (result, descr)
    self.send(msg)

Contact.buildStarted = buildStarted
Contact.buildFinished = buildFinished


## def send_message(message, test=False):
##     import subprocess
##     return subprocess.call([
##             '/tmp/commit-bot/message',
##             '#buildbot-test',
##             message])
## send_message(color(BOLD+PURPLE, 'ciao'))
