import py
html = py.xml.html

from buildbot.status.web.base import HtmlResource

# xxx caching?
class RevisionOutcomeSet(object):

    def __init__(self, rev):
        self.revision = rev
        self._outcomes = {}
        self.failed = set()
        self.skipped = set()
        # xxx failure tracebacks

    def populate_one(self, name, shortrepr):
        namekey = name.split(':', 1) # xxx not always the correct thing
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


class GatherOutcomeSet(object):

    def __init__(self, map):
        self.map = map
        self._failed = None
        self._skipped = None
        self.revision = map.values()[0].revision
        

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
         
# ________________________________________________________________

N = 10

def colsizes(namekeys):
    colsizes = None
    for keys in namekeys:
        if colsizes is None:
            colsizes = [0] * len(keys)
        colsizes = map(max, zip(map(len, keys), colsizes))

    return colsizes
    

class SummaryPage(object):

    def __init__(self):
        self.sections = []

    def add_section(self, outcome_sets):
        by_rev = sorted((outcome_set.revision, outcome_set) for outcome_set
                         in outcome_sets)
        lines = []
        def bars():
            return ' |'*len(lines)
        for rev, outcome_set in by_rev:
            count_failures = len(outcome_set.failed)
            count_skipped = len(outcome_set.skipped)
            lines.append("%s %d" % (bars(),rev))
        lines.append(bars())

        failed = set()
        for rev, outcome_set in by_rev:            
            failed.update(outcome_set.failed)

        colwidths = colsizes(failed)

        for failure in sorted(failed):
            line = []
            for rev, outcome_set in by_rev:
                letter = outcome_set.get_outcome(failure)
                line.append(" %s" % letter)
            for width, key in zip(colwidths, failure):
                line.append("  %-*s" % (width, key))
            lines.append(''.join(line))
        
        section = html.pre('\n'.join(lines))
        self.sections.append(section)

    def render(self):
        body_html = html.div(self.sections)
        return body_html.unicode()


class Summary(HtmlResource):

    def recentRevisions(self, request):
        # xxx branches
        status = self.getStatus(request)
        revs = {}
        for builderName in status.getBuilderNames():
            builderStatus = status.getBuilder(builderName)
            for build in builderStatus.generateFinishedBuilds(num_builds=N):
                rev = int(build.getProperty("got_revision"))
                revBuilds = revs.setdefault(rev, {})
                if builderName not in revBuilds: # pick the most recent or ?
                    # xxx hack, go through the steps and make sure
                    # the log is there
                    log = [log for log in build.getLogs()
                           if log.getName() == "pytestLog"][0]
                    outcome_set = RevisionOutcomeSet(rev)
                    outcome_set.populate(log)
                    revBuilds[builderName] = outcome_set
        return revs
                            
    def body(self, request):
        revs = self.recentRevisions(request)
        outcome_sets = []
        for rev, by_build in revs.items():
            outcome_sets.append(GatherOutcomeSet(by_build))
        page = SummaryPage()
        page.add_section(outcome_sets)        
        return page.render()
