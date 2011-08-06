import time

RED = 31
GREEN = 32
YELLOW = 33
BLUE = 34
MAGENTA = 35
CYAN = 36
GRAY = 37

def color(s, fg=1, bg=1):
    template = '\033[%02d;%02dm%s\033[0m'
    return template % (bg, fg, s)

def handle_commit(payload, commit, test=False):
    author = commit['author']
    node = commit['node']
    timestamp = commit.get('timestamp')
    curtime = time.strftime('[%Y-%m-%d %H:%M]')
    log = '%s %s %s %s' % (curtime, node, timestamp, author)
    print color(log, fg=GREEN)
