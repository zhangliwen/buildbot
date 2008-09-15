
from buildbot.status.web.base import HtmlResource

# xxx caching?
class RevOutcome(object):

    def __init__(self, rev):
        self.rev = rev
        self._outcomes = {}
        self.failed = set()
        self.skipped = set()
        # xxx failure tracebacks

    def populate_one(self, name, shortrepr):
        namekey = name.split(':', 1)
        if namekey[0].endswith('.py'):
            namekey[0] = namekey[0][:-3].replace('/', '.')

        namekey = tuple(namekey)
        self._outcomes[namekey] = shortrepr
        if shortrepr == 's':
            self.skipped.add(namekey)
        elif shortrepr == '.':
            pass
        else:
            self.failed.add(namekey)

    def populate(self, log):
        for line in log.readlines():
            kind = line[0]
            if kind == ' ':
                continue
            name = line[2:].rstrip()
            self.populate_one(name, kind)

    def get_outcome(self, namekey):
        return self._outcomes[namekey]


class GatherOutcome(object):

    def __init__(self, map):
        self.map = map
        self._failed = None
        self._skipped = None

    @property
    def failed(self):
        if self._failed is None:
            self._failed = set()
            for prefix, outcome in self.map.items():
                self._failed.update([(prefix,)+ namekey for namekey in
                                     outcome.failed])
        return self._failed

    @property
    def skipped(self):
        if self._skipped is None:
            self._skipped = set()
            for prefix, outcome in self.map.items():
                self._skipped.update([(prefix,) + namekey for namekey in
                                     outcome.skipped])
        return self._skipped

    def get_outcome(self, namekey):
        return self.map[namekey[0]].get_outcome(namekey[1:])
         


N = 10

class Summary(HtmlResource):

    def recentRevisions(self, request):
        # xxx branches
        status = self.getStatus(request)
        revs = {}
        for builderName in status.getBuilderNames():
            builderStatus = status.getBuilder(builderName)
            for build in builderStatus.generateFinishedBuilds(num_builds=N):
                rev = build.getProperty("got_revision")
                revBuilds = revs.setdefault(rev, {})
                if builderName not in revBuilds: # pick the most recent or ?
                    # xxx hack, go through the steps and make sure
                    # the log is there
                    log = [log for log in build.getLogs()
                           if log.getName() == "pytestLog"][0]
                    revBuilds[builderName] = RevOutcome(log)
        revs = revs.items()
        revs.sort()
        return revs
                            
    def body(self, request):
        revs = self.recentRevisions(request)
        return repr(len(revs))
