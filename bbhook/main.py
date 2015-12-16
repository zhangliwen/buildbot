#!/usr/bin/env python

"""
POST hook for bitbucket. So far, it just sends the email diff.

The idea is that the buildmaster user runs it inside a screen session on
codespeak.
"""

import json
import traceback
import pprint
import sys
import flask
import py


app = flask.Flask(__name__)



@app.route('/', methods=['GET'])
def test_form():
    """Respond to a GET request."""
    return """
        <html>
            <p>
                This is the pypy bitbucket hook.
                Use the following form only for testing
            </p>
            <form method=post>
                payload: <input name=payload> <br>
                submit: <input type=submit>
            </form>
        </html>
    """


@app.route('/', methods=['POST'])
def handle_payload():
    open('/tmp/payload', 'w').write(flask.request.form['payload'])
    try:
        payload = json.loads(flask.request.form['payload'])
        from . import hook
        hook.handle(payload, test=app.testing)
    except:
        traceback.print_exc()
        print >> sys.stderr, 'payload:'
        pprint.pprint(payload, sys.stderr)
        print >> sys.stderr
        raise
    return 'ok'


class DefaultConfig(object):
    LOCAL_REPOS = py.path.local(__file__).dirpath('repos')
    REMOTE_BASE = 'http://bitbucket.org'
    USE_COLOR_CODES = True
    LISTFILES = False
    #
    DEFAULT_USER = 'pypy'
    DEFAULT_REPO = 'pypy'


class BuildbotConfig(DefaultConfig):
    SMTP_SERVER = 'smtp.gmail.com'
    SMTP_PORT = 25
    SMTP_TLS = True
    SMTP_USERNAME = 'pypy.commits@gmail.com'
    SMTP_PASSWORD = py.path.local(__file__).dirpath('smtp.password').read().strip()
    ADDRESS = 'pypy-commit@python.org'
    #
    CHANNEL = '#pypy'
    #BOT = '/svn/hooks/commit-bot/message'
    BOT = '/home/buildmaster/commit-bot/message'


app.config.from_object(BuildbotConfig)
