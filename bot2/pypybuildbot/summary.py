import urllib

import py
html = py.xml.html

from buildbot.status.web.base import HtmlResource

class RevisionOutcomeSet(object):

    def __init__(self, rev, key=None, run_stdio=None):
        self.revision = rev
        self.key = key
        self._outcomes = {}
        self.failed = set()
        self.skipped = set()
        self.longreprs = {}
        self._run_stdio = run_stdio

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
        return self._outcomes.get(namekey, ' ')

    def get_longrepr(self, namekey):
        return self.longreprs.get(namekey, '')

    def get_key_namekey(self, namekey):
        return (self.key, namekey)

    def get_run_stdios(self):
        return {self.key: (self, self._run_stdio)}

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
        pytest_log = None
        stdio_url = "no_log"
        for step in build.getSteps():
            logs = dict((log.getName(), log) for log in step.getLogs())
            if 'pytestLog' in logs:
                pytest_log = logs['pytestLog']
                stdio_url = status.getURLForThing(logs['stdio'])
                # builbot is broken in this :(
                stdio_url = stdio_url[:-1]+"stdio"
                break

        outcome_set = RevisionOutcomeSet(rev, key, stdio_url) 
        if pytest_log is None or not pytest_log.hasContents():
            outcome_set.populate_one('<run>', '!', "no log from the test run")
        else:
            outcome_set.populate(pytest_log)
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
        which = namekey[0]
        if which not in self.map:
            return ' '
        return self.map[which].get_outcome(namekey[1:])

    def get_longrepr(self, namekey):
        which = namekey[0]
        if which not in self.map:
            return ''
        return self.map[which].get_longrepr(namekey[1:])

    def get_key_namekey(self, namekey):
        return self.map[namekey[0]].get_key_namekey(namekey[1:])

    def get_run_stdios(self):
        all = {}
        for outcome_set in self.map.itervalues():
            all.update(outcome_set.get_run_stdios())
        return all
         
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

    def make_stdio_anchors_for(self, outcome_set):
        anchors = []
        stdios = sorted(outcome_set.get_run_stdios().items())
        for cachekey, (run, url) in stdios:
            builder = cachekey[0]
            anchors.append('  ')
            text = "%s [%d failed; %d skipped]" % (builder,
                                                   len(run.failed),
                                                   len(run.skipped))
            anchors.append(html.a(text, href=url))
        return anchors

    def add_title(self, title):
        self.sections.append(html.h2(title))
        
    def add_section(self, outcome_sets):
        revs = sorted(outcome_set.revision for outcome_set in outcome_sets)
        by_rev = sorted((outcome_set.revision, outcome_set) for outcome_set
                         in outcome_sets)
        lines = []

        align = 2*len(revs)-1+len(str(revs[-1]))
        def bars():
            return ' |'*len(lines)
        for rev, outcome_set in by_rev:
            count_failures = len(outcome_set.failed)
            count_skipped = len(outcome_set.skipped)
            line = ["%s %d" % (bars(),rev)]
            line.append((align-len(line[0]))*" ")
            line.append(self.make_stdio_anchors_for(outcome_set))
            line.append('\n')
            lines.append(line)
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

    def add_no_revision_builds(self, status, no_revision_builds):
        section = html.div(html.p("builds aborted without getting"
                                  " a revision:"))

        for build in no_revision_builds:
            builderName = build.getBuilder().getName()
            num = build.getNumber()
            descr = "%s #%d" % (builderName, num)
            url = status.getURLForThing(build)
            section.append(html.a(descr, href=url))
            section.append(html.br())
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

def getProp(obj, name, default=None):
    try:
        return obj.getProperty(name)
    except KeyError:
        return default
    
class Summary(HtmlResource):

    def __init__(self):
        HtmlResource.__init__(self)
        self.putChild('longrepr', LongRepr())

    def getTitle(self, request):
        status = self.getStatus(request)        
        return "%s: summaries of last %d revisions" % (status.getProjectName(),
                                                       N)

    @staticmethod
    def _prune_revs(revs, cutnum):
        if len(revs) > cutnum:
            for rev in sorted(revs.keys())[:-cutnum]:
                del revs[rev]

    def recentRevisions(self, status):
        branches = {}

        for builderName in status.getBuilderNames():
            builderStatus = status.getBuilder(builderName)
            for build in builderStatus.generateFinishedBuilds(num_builds=5*N):
                branch = getProp(build, 'branch')
                got_rev = getProp(build, 'got_revision', None)

                revs, no_revision_builds = branches.setdefault(branch,
                                                               ({}, []))

                if got_rev is None:
                    no_revision_builds.append(build)
                else:
                    rev = int(got_rev)
                    revBuilds = revs.setdefault(rev, {})
                    # pick the most recent or ?
                    if builderName not in revBuilds:
                        key = (builderName, build.getNumber())
                        outcome_set = outcome_set_cache.get(status, key)
                        revBuilds[builderName] = outcome_set

        for branch, (revs, no_revision_builds) in branches.items():
            self._prune_revs(revs, N)
                            
        return branches
                            
    def body(self, request):
        status = self.getStatus(request)

        page = SummaryPage()
        
        branches = self.recentRevisions(status)

        for branch, (revs, no_revision_builds) in sorted(branches.iteritems()):
            outcome_sets = []
            for rev, by_build in revs.items():
                outcome_sets.append(GatherOutcomeSet(by_build))
            if branch is None:
                branch = "<trunk>"
            page.add_title(branch)
            page.add_section(outcome_sets)
            page.add_no_revision_builds(status, no_revision_builds)

        return page.render()
