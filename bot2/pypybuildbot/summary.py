import urllib

import py
html = py.xml.html

from buildbot.status.web.base import HtmlResource

class RevisionOutcomeSet(object):

    def __init__(self, rev, key=None):
        self.revision = rev
        self.key = key
        self._outcomes = {}
        self.failed = set()
        self.skipped = set()
        self.longreprs = {}

    def populate_one(self, name, shortrepr, longrepr=None):
        if shortrepr == '!':
            namekey = [name, '']
        else:        
            namekey = name.split(':', 1)
            if namekey[0].endswith('.py'):
                namekey[0] = namekey[0][:-3].replace('/', '.')
            if len(namekey) == 1:
                namekey.append('')

        namekey = tuple(namekey)
        self._outcomes[namekey] = shortrepr
        if shortrepr == 's':
            self.skipped.add(namekey)
        elif shortrepr == '.':
            pass
        else:
            self.failed.add(namekey)

        if longrepr:
            self.longreprs[namekey] = longrepr

    def populate(self, log):
        kind = None
        def add_one():
            if kind is not None:
                self.populate_one(name, kind, ''.join(longrepr))        
        for line in log.readlines():
            first = line[0]
            if first == ' ':
                longrepr.append(line[1:])
                continue
            add_one()
            kind = first
            name = line[2:].rstrip()
            longrepr = []
        add_one()

    def get_outcome(self, namekey):
        return self._outcomes[namekey]

    def get_key_namekey(self, namekey):
        return (self.key, namekey)

    def get_longrepr(self, namekey):
        return self.longreprs.get(namekey, '')

class RevisionOutcomeSetCache(object):
    CACHESIZE = 10

    def __init__(self):
        self._outcome_sets = {}
        self._lru = []

    def _load_outcome_set(self, status, key):
        builderName, buildNumber = key
        builderStatus = status.getBuilder(builderName)
        build = builderStatus.getBuild(buildNumber)

        rev = int(build.getProperty("got_revision"))
        log = None
        for step in build.getSteps():
            candLogs = [log for log in step.getLogs()
                        if log.getName() == "pytestLog"]
            if candLogs:
                log = candLogs[0]
                break

        outcome_set = RevisionOutcomeSet(rev, key) 
        if log is None or not log.hasContents():
            outcome_set.populate_one('<run>', '!', "no log from the test run")
        else:
            outcome_set.populate(log)
        return outcome_set
        
    def get(self, status, key):
        try:
            self._lru.remove(key)
        except ValueError:
            pass
        self._lru.append(key)
        try:
            return self._outcome_sets[key]
        except KeyError:
            pass
        if len(self._lru) > self.CACHESIZE:
            dead_key = self._lru.pop(0)
            self._outcome_sets.pop(dead_key, None)
        outcome_set = self._load_outcome_set(status, key)
        self._outcome_sets[key] = outcome_set
        return outcome_set

outcome_set_cache = RevisionOutcomeSetCache()

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

    def get_key_namekey(self, namekey):
        return self.map[namekey[0]].get_key_namekey(namekey[1:])

    def get_longrepr(self, namekey):
        return self.map[namekey[0]].get_longrepr(namekey[1:])
         
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

    def make_longrepr_url_for(self, outcome_set, namekey):
        cachekey, namekey = outcome_set.get_key_namekey(namekey)
        parms={
            'builder': cachekey[0],
            'build': cachekey[1],
            'mod': namekey[0],
            'testname': namekey[1]
            }
        qs = urllib.urlencode(parms)
        return "/summary/longrepr?" + qs

    def add_section(self, outcome_sets):
        by_rev = sorted((outcome_set.revision, outcome_set) for outcome_set
                         in outcome_sets)
        lines = []
        def bars():
            return ' |'*len(lines)
        for rev, outcome_set in by_rev:
            count_failures = len(outcome_set.failed)
            count_skipped = len(outcome_set.skipped)
            lines.append(["%s %d" % (bars(),rev), "\n"])
        lines.append([bars(), "\n"])
        
        failed = set()
        for rev, outcome_set in by_rev:            
            failed.update(outcome_set.failed)

        colwidths = colsizes(failed)

        for failure in sorted(failed):
            line = []
            for rev, outcome_set in by_rev:
                letter = outcome_set.get_outcome(failure)
                if outcome_set.get_longrepr(failure):
                    longrepr_url = self.make_longrepr_url_for(outcome_set,
                                                              failure)
                    line.append([" ",html.a(letter, href=longrepr_url)])
                else:
                    line.append(" %s" % letter)
            for width, key in zip(colwidths, failure):
                line.append("  %-*s" % (width, key))
            lines.append(line)
            lines.append("\n")
        
        section = html.pre(lines)
        self.sections.append(section)

    def render(self):
        body_html = html.div(self.sections)
        return body_html.unicode()

class LongRepr(HtmlResource):

    def get_namekey(self, request):
        mod = request.args.get('mod', [])
        if not mod:
            mod = None
        else:
            mod = mod[0]
        
        testname = request.args.get('testname', [])
        if testname:
            testname = testname[0]
        else:
            testname = ''

        return (mod, testname)
        
    def getTitle(self, request):
        mod, testname = self.get_namekey(request)
        if mod is None:
            return "no such test"
        return "%s %s" % (mod, testname)        

    def body(self, request):
        builder = request.args.get('builder', [])
        build = request.args.get('build', [])
        if not builder or not build:
            return "no such build"
        builderName = builder[0]
        buildNumber = int(build[0])

        outcome_set = outcome_set_cache.get(self.getStatus(request),
                                            (builderName,
                                             buildNumber))

        namekey = self.get_namekey(request)

        longrepr = outcome_set.get_longrepr(namekey)

        return html.pre(longrepr).unicode()


class Summary(HtmlResource):
    title="Summary" # xxx

    def __init__(self):
        HtmlResource.__init__(self)
        self.putChild('longrepr', LongRepr())

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
                    key = (builderName, build.getNumber())
                    outcome_set = outcome_set_cache.get(status, key)
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
