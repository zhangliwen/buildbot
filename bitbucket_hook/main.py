#!/usr/bin/env python

"""
POST hook for bitbucket. So far, it just sends the email diff.

The idea is that the buildmaster user runs it inside a screen session on
codespeak.
"""

import time
import json
import traceback
import pprint
import sys
import flask

app = flask.Flask('bb-hook')

import hook

HOST_NAME = 'codespeak.net'
PORT_NUMBER = 9237

@app.route('/', methods=['GET'])
def test_form():
    """Respond to a GET request."""
    return """
        <html>
            <p>This is the pypy bitbucket hook. Use the following form only for testing</p>
            <form method=post>
                payload: <input name=payload> <br>
                submit: <input type=submit>
            </form>
        </html>
    """



@app.route('/', methods=['POST'])
def handle_payload():
    payload = json.loads(flask.request.form['payload'])
    try:
        handler = hook.BitbucketHookHandler()
        handler.handle(payload)
    except:
        traceback.print_exc()
        print >> sys.stderr, 'payload:'
        pprint.pprint(payload, sys.stderr)
        print >> sys.stderr
        raise

if __name__ == '__main__':
    app.run(debug=True)
