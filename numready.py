#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This should be run under PyPy.
"""

import platform
import subprocess
import sys
import tempfile
import webbrowser
from collections import OrderedDict

import jinja2


MODULE_SEARCH_CODE = """
import types
import {modname} as numpy

for name in dir(numpy):
    if name.startswith("_"):
        continue
    obj = getattr(numpy, name)
    kind = "{kinds[UNKNOWN]}"
    if isinstance(obj, types.TypeType):
        kind = "{kinds[TYPE]}"
    print kind, ":", name
"""

ATTR_SEARCH_CODE = """
import types
import {modname} as numpy

obj = getattr(numpy, "{name}")
for name in dir(obj):
    if name.startswith("_"):
        continue
    sub_obj = getattr(obj, name)
    kind = "{kinds[UNKNOWN]}"
    if isinstance(sub_obj, types.TypeType):
        kind = "{kinds[TYPE]}"
    print kind, ":", name
"""

KINDS = {
    "UNKNOWN": "U",
    "TYPE": "T",
}

PAGE_TEMPLATE = u"""
<!DOCTYPE html>
<html lang="en">
    <head>
        <title>NumPyPy Status</title>
        <meta http-equiv="content-type" content="text/html; charset=utf-8">
        <style type="text/css">
            body {
                font-family: 'Consolas', 'Bitstream Vera Sans Mono', monospace;
            }
            h1 {
                text-align: center;
            }
            table {
                border: 8px solid #DFDECB;
                margin: 30px auto;
                font-size: 12px;
            }
            table th {
                text-align: left;
            }
            table td {
                padding: 4px 10px;
                text-align: center;
            }
            tr.exists {
                background-color: #337792;
                color: white;
                border: 1px solid #234F61;
            }
        </style>
    </head>
    <body>
        <h1>NumPyPy Status</h1>
        <table>
            <thead>
                <tr>
                    <th></th>
                    <th>PyPy</th>
                </tr>
            </thead>
            <tbody>
                {% for item in all_items %}
                    <tr{% if item.pypy_exists %} class="exists"{% endif %}>
                        <th>{{ item.name }}</th>
                        <td>{% if item.pypy_exists %}✔{% else %}✖{% endif %}</td>
                    </tr>
                    {% if item.subitems %}
                        {% for item in item.subitems %}
                            <tr{% if item.pypy_exists %} class="exists"{% endif %}>
                                <th>&nbsp;&nbsp;&nbsp;{{ item.name }}</th>
                                <td>{% if item.pypy_exists %}✔{% else %}✖{% endif %}</td>
                            </tr>
                        {% endfor %}
                    {% endif %}
                {% endfor %}
            </tbody>
        </table>
    </body>
</html>
"""

class SearchableSet(object):
    def __init__(self, items=()):
        self._items = {}
        for item in items:
            self.add(item)

    def __iter__(self):
        return iter(self._items)

    def __contains__(self, other):
        return other in self._items

    def __getitem__(self, idx):
        return self._items[idx]

    def add(self, item):
        self._items[item] = item

class Item(object):
    def __init__(self, name, kind, subitems=None):
        self.name = name
        self.kind = kind
        self.subitems = subitems

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return self.name == other.name


class ItemStatus(object):
    def __init__(self, name, pypy_exists, subitems=None):
        self.name = name
        self.pypy_exists = pypy_exists
        self.subitems = subitems

    def __lt__(self, other):
        return self.name < other.name

def find_numpy_attrs(python, modname, name):
    lines = subprocess.check_output(
        [python, "-c", ATTR_SEARCH_CODE.format(modname=modname, kinds=KINDS, name=name)]
    ).splitlines()
    items = SearchableSet()
    for line in lines:
        kind, name = line.split(" : ", 1)
        items.add(Item(name, kind))
    return items

def find_numpy_items(python, modname="numpy"):
    lines = subprocess.check_output(
        [python, "-c", MODULE_SEARCH_CODE.format(modname=modname, kinds=KINDS)]
    ).splitlines()
    items = SearchableSet()
    for line in lines:
        kind, name = line.split(" : ", 1)
        subitems = None
        if kind == KINDS["TYPE"]:
            subitems = find_numpy_attrs(python, modname, name)
        items.add(Item(name, kind, subitems))
    return items

def main(argv):
    assert platform.python_implementation() == "PyPy"

    cpy_items = find_numpy_items("/usr/bin/python")
    pypy_items = find_numpy_items(sys.executable, "numpypy")
    all_items = []

    for item in cpy_items:
        pypy_exists = item in pypy_items
        subitems = None
        if item.subitems:
            subitems = []
            for sub in item.subitems:
                subitems.append(
                    ItemStatus(sub.name, pypy_exists=pypy_exists and pypy_items[item].subitems and sub in pypy_items[item].subitems)
                )
            subitems = sorted(subitems)
        all_items.append(
            ItemStatus(item.name, pypy_exists=item in pypy_items, subitems=subitems)
        )

    html = jinja2.Template(PAGE_TEMPLATE).render(all_items=sorted(all_items))
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(html.encode("utf-8"))
    webbrowser.open_new_tab(f.name)


if __name__ == '__main__':
    main(sys.argv)