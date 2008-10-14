import urllib, time

import py
html = py.xml.html

from buildbot.status.web.base import HtmlResource
from buildbot.status.builder import FAILURE, EXCEPTION

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

    @property
    def numpassed(self):
        return len(self._outcomes) - len(self.skipped) - len(self.failed)

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

    def __init__(self, cachesize=10):
        self._outcome_sets = {}
        self._lru = []
        self._hits = 0
        self._misses = 0
        self.cachesize = cachesize

    def reset(self):
        self._hits = 0
        self._misses = 0

    def stats(self):
        return "hits: %d, misses: %d" % (self._hits, self._misses)

    def _load_outcome_set(self, status, key):
        builderName, buildNumber = key
        builderStatus = status.getBuilder(builderName)
        build = builderStatus.getBuild(buildNumber)

        rev = int(build.getProperty("got_revision"))
        pytest_log = None
        stdio_log = None
        failure = None
        for step in build.getSteps():
            logs = dict((log.getName(), log) for log in step.getLogs())
            if 'pytestLog' in logs:
                pytest_log = logs['pytestLog']
                stdio_log = logs['stdio']
                break
            elif (stdio_log is None and
                  step.getResults()[0] in (FAILURE, EXCEPTION)):
                failure = ' '.join(step.getText())
                stdio_log = logs.get('stdio')

        if stdio_log is None:
            stdio_url = "no_log"
        else:
            stdio_url = status.getURLForThing(stdio_log)
            # builbot is broken in this :(
            stdio_url = stdio_url[:-1]+"stdio"
            
        outcome_set = RevisionOutcomeSet(rev, key, stdio_url) 
        if pytest_log is None or not pytest_log.hasContents():
            name = failure or '<run>'
            outcome_set.populate_one(name, '!', "no log from the test run")
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
            outcome_set = self._outcome_sets[key]
            self._hits += 1
            return outcome_set
        except KeyError:
            pass
        self._misses += 1
        if len(self._lru) > self.cachesize:
            dead_key = self._lru.pop(0)
            self._outcome_sets.pop(dead_key, None)
        outcome_set = self._load_outcome_set(status, key)
        self._outcome_sets[key] = outcome_set
        return outcome_set

class GatherOutcomeSet(object):

    def __init__(self, map):
        self.map = map
        self._failed = None
        self._skipped = None
        self._numpassed = None
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

    @property
    def numpassed(self):
        if self._numpassed is None:
            numpassed = 0
            for  prefix, outcome in self.map.items():
                numpassed += outcome.numpassed
            self._numpassed = numpassed
        return self._numpassed

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

N = 5

outcome_set_cache = RevisionOutcomeSetCache(10*(N+1))


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
        self.cur_branch=None

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
            text = "%s [%d, %d F, %d s]" % (builder,
                                            run.numpassed,
                                            len(run.failed),
                                            len(run.skipped))
            anchors.append(html.a(text, href=url))
        return anchors

    def start_branch(self, branch):
        self.cur_branch = branch
        branch_anchor = html.a(branch, href="/summary?branch=%s" % branch)
        self.sections.append(html.h2(branch_anchor))

    def _rev_anchor(self, rev):
        rev_anchor = html.a(str(rev), href="/summary?branch=%s&recentrev=%d" %
                            (self.cur_branch, rev))
        return rev_anchor
                            
    def add_section(self, outcome_sets):
        if not outcome_sets:
            return
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
            line = [bars(), ' ', self._rev_anchor(rev)]
            line.append((align-len(line[0]))*" ")
            line.append(self.make_stdio_anchors_for(outcome_set))
            line.append('\n')
            lines.append(line)
        lines.append([bars(), "\n"])
        
        failed = set()
        exploded = set()
        for rev, outcome_set in by_rev:
            for failure in outcome_set.failed:
                letter = outcome_set.get_outcome(failure)
                if letter == '!':
                    exploded.add(failure)
                failed.add(failure)

        colwidths = colsizes(failed)

        def sorting(x):
            return (x not in exploded, x)

        for failure in sorted(failed, key=sorting):
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

    def add_comment(self, comm):
        self.sections.append(py.xml.raw("<!-- %s -->" % comm))

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
        t0 = time.time()
        outcome_set_cache.reset()
        
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

        return html.div([html.pre(longrepr),
                         py.xml.raw("<!-- %s -->" % outcome_set_cache.stats())
                         ]).unicode()

def getProp(obj, name, default=None):
    try:
        return obj.getProperty(name)
    except KeyError:
        return default

def make_test(lst):
    if lst is None:
        return lambda v: True
    else:
        membs = set(lst)
        return lambda v: v in membs

def make_subst(v1, v2):
    def subst(v):
        if v == v1:
            return v2
        return v
    return subst

trunk_name = make_subst(None, "<trunk>")
trunk_value = make_subst("<trunk>", None)

    
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

    def recentRevisions(self, status, only_recentrevs=None, only_branches=None):
        test_rev = make_test(only_recentrevs)
        test_branch = make_test(only_branches)
        
        branches = {}

        for builderName in status.getBuilderNames():
            builderStatus = status.getBuilder(builderName)
            for build in builderStatus.generateFinishedBuilds(num_builds=5*N):
                branch = getProp(build, 'branch')
                if not test_branch(branch):
                    continue
                got_rev = getProp(build, 'got_revision', None)
                if not test_rev(got_rev):
                    continue

                revs, no_revision_builds = branches.setdefault(branch,
                                                               ({}, []))

                if got_rev is None:
                    no_revision_builds.append(build)
                else:
                    rev = int(got_rev)
                    revBuilds = revs.setdefault(rev, {})
                    # pick the most recent or ?
                    if builderName not in revBuilds:
                        revBuilds[builderName] = build.getNumber()

        for branch, (revs, no_revision_builds) in branches.items():
            self._prune_revs(revs, N)
            for rev, revBuilds in revs.iteritems():
                for builderName, buildNumber in revBuilds.items():
                    key = (builderName, buildNumber)
                    outcome_set = outcome_set_cache.get(status, key)
                    revBuilds[builderName] = outcome_set
                            
        return branches
                            
    def body(self, request):
        t0 = time.time()
        outcome_set_cache.reset()
        
        status = self.getStatus(request)

        page = SummaryPage()
        #page.sections.append(repr(request.args))
        
        only_branches = request.args.get('branch', None)
        only_recentrevs = request.args.get('recentrev', None)
        if only_branches is not None:
            only_branches = map(trunk_value, only_branches)
        
        branches = self.recentRevisions(status,
                                        only_recentrevs=only_recentrevs,
                                        only_branches=only_branches)

        for branch, (revs, no_revision_builds) in sorted(branches.iteritems()):
            outcome_sets = []
            for rev, by_build in revs.items():
                outcome_sets.append(GatherOutcomeSet(by_build))
            branch = trunk_name(branch)
            page.start_branch(branch)
            page.add_section(outcome_sets)
            page.add_no_revision_builds(status, no_revision_builds)

        t1 = time.time()
        total_time = time.time()-t0
        page.add_comment('t=%.2f; %s' % (total_time,
                                         outcome_set_cache.stats()))
        return page.render()
