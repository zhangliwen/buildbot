import os.path
import datetime
import itertools
import re
import py
from twisted.web import resource
from twisted.web.static import File, DirectoryLister

class PyPyTarball(object):

    # to get the desired order keep in mind that they are reversed at the end,
    # so the highest the value, the bigger the priority
    FEATURES_PRIORITY = {
        'jit':      100,
        'nojit':     50,
        'stackless': 10
        }

    PLATFORM_PRIORITY = {
        'linux':    100,
        'linux64':   50,
        'osx':       30,
        'win32':     10,
        }

    PLATFORMS = {
        'linux':   'linux-x86-32',
        'linux64': 'linux-x86-64',
        'osx':     'macosx-x86-32',
        'win32':   'win-x86-32',        
        }

    DESCRIPTIONS = {
        'nojit':     'app-level',
        'jit':       'jit',
        'stackless': 'stackless-app-level',
        }

    def __init__(self, filename):
        self.filename = filename
        try:
            self.parse_filename()
        except ValueError:
            self.exe = None
            self.backend = None
            self.features = None
            self.rev = -1
            self.platform = None

    def parse_filename(self):
        if not self.filename.endswith('.tar.bz2'):
            raise ValueError
        name = self.filename.replace('.tar.bz2', '')
        self.exe, self.backend, self.features, self.rev, self.platform = name.split('-')

    def key(self):
        return (self.rev,
                self.FEATURES_PRIORITY.get(self.features, -1),
                self.PLATFORM_PRIORITY.get(self.platform, -1))

    def get_builder_names(self):
        platform = self.PLATFORMS.get(self.platform, self.platform)
        description = self.DESCRIPTIONS.get(self.features, self.features)
        own_builder = 'own-%s' % platform
        app_builder = '%s-%s-%s-%s' % (self.exe, self.backend, description, platform)
        return own_builder, app_builder


class PyPyList(File):

    def listNames(self):
        names = File.listNames(self)
        items = map(PyPyTarball, names)
        items.sort(key=PyPyTarball.key, reverse=True)
        return [item.filename for item in items]

    def directoryListing(self):
        def is_pypy_dir(names):
            for name in names:
                if name.startswith('pypy-c'):
                    return True
            return False
        names = self.listNames()
        if is_pypy_dir(names):
            Listener = PyPyDirectoryLister
        else:
            Listener = DirectoryLister
        return Listener(self.path,
                        names,
                        self.contentTypes,
                        self.contentEncodings,
                        self.defaultType)



class PyPyDirectoryLister(DirectoryLister):
    template = """<html>
<head>
<title>%(header)s</title>
<style>
.even        { background-color: #eee    }
.odd         { background-color: #dedede }
.even-passed { background-color: #caffd8 }
.odd-passed  { background-color: #a3feba }
.even-failed { background-color: #ffbbbb }
.odd-failed  { background-color: #ff9797 }

.summary_link {
    color: black;
    text-decoration: none;
}
.summary_link:hover {
    color: blue;
    text-decoration: underline;
}

.icon { text-align: center }
.listing {
    margin-left: auto;
    margin-right: auto;
    width: 50%%;
    padding: 0.1em;
    }

body { border: 0; padding: 0; margin: 0; background-color: #efefef; }
h1 {padding: 0.1em; background-color: #777; color: white; border-bottom: thin white dashed;}
td,th {padding-left: 0.5em; padding-right: 0.5em; }

</style>
</head>

<body>
<h1>%(header)s</h1>

<table>
    <thead>
        <tr>
            <th>Filename</th>
            <th>Size</th>
            <th>Date</th>
            <th><i>own</i> tests</th>
            <th><i>applevel</i> tests</th>
        </tr>
    </thead>
    <tbody>
%(tableContent)s
    </tbody>
</table>

</body>
</html>
"""

    linePattern = """<tr class="%(class)s">
    <td><a href="%(href)s">%(text)s</a></td>
    <td>%(size)s</td>
    <td>%(date)s</td>
    <td class="%(own_summary_class)s"><a class="summary_link" href="%(own_href)s">%(own_summary)s</a></td>
    <td class="%(app_summary_class)s"><a class="summary_link" href="%(app_href)s">%(app_summary)s</a></td>
</tr>
"""

    def render(self, request):
        self.status = request.site.buildbot_service.getStatus()
        return DirectoryLister.render(self, request)

    def _buildTableContent(self, elements):
        tableContent = []
        rowClasses = itertools.cycle(['odd', 'even'])
        for element, rowClass in zip(elements, rowClasses):
            element["class"] = rowClass
            result = self._add_test_results(element, rowClass)
            tableContent.append(self.linePattern % element)
        return tableContent

    def _add_test_results(self, element, rowClass):
        filename = element['href']
        f = py.path.local(self.path).join(filename)
        date = datetime.date.fromtimestamp(f.mtime())
        element['date'] = date.isoformat()
        t = PyPyTarball(filename)
        own_builder, app_builder = t.get_builder_names()
        self._add_result_for_builder(element, own_builder, 'own_', t.rev, rowClass)
        self._add_result_for_builder(element, app_builder, 'app_', t.rev, rowClass)

    def _add_result_for_builder(self, element, builder_name, prefix, rev, rowClass):
        branch = self._get_branch()
        summary, category = self._get_summary_and_category(builder_name, branch, rev)
        if branch == 'trunk':
            branch = '%3Ctrunk%3E' # <trunk>
        if category:
            href = '/summary?category=%s&branch=%s&recentrev=%s' % (category, branch, rev)
        else:
            href = '#'
        element[prefix + 'summary'] = summary
        element[prefix + 'summary_class'] = self._get_summary_class(summary, rowClass)
        element[prefix + 'href'] = href

    def _get_branch(self):
        parts = self.path.split(os.path.sep)
        i = parts.index('nightly')
        branch = os.path.sep.join(parts[i+1:])
        return branch

    def _get_summary_and_category(self, builder_name, branch, rev):
        try:
            builder = self.status.getBuilder(builder_name)
            return builder.summary_by_branch_and_revision[(branch, rev)], builder.category
        except (AttributeError, KeyError):
            return None, None
            # for testing
            ## from pypybuildbot.summary import OutcomeSummary
            ## import random
            ## if random.choice([True, True, True, False]):
            ##     return OutcomeSummary(1000, 0, 2, 4), None
            ## else:
            ##     return OutcomeSummary(990, 10, 2, 4), None

    def _get_summary_class(self, summary, rowClass):
        if summary is None:
            return rowClass
        elif summary.is_ok():
            return rowClass + '-passed'
        else:
            return rowClass + '-failed'

