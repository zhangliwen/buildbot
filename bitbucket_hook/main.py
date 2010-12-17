#!/usr/bin/env python

"""
POST hook for bitbucket. So far, it just sends the email diff.

The idea is that the buildmaster user runs inside a screen session on codespeak.
"""

import time
import BaseHTTPServer
import json
import cgi

from hook import BitbucketHookHandler

HOST_NAME = 'codespeak.net'
PORT_NUMBER = 9237

class MyHandler(BaseHTTPServer.BaseHTTPRequestHandler):

    def do_GET(self):
        """Respond to a GET request."""
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write("This is the pypy bitbucket hook.")

    def do_POST(self):
        length = int(self.headers['Content-Length'])
        query_string = self.rfile.read(length)
        data = dict(cgi.parse_qsl(query_string))
        payload = json.loads(data['payload'])
        handler = BitbucketHookHandler()
        handler.handle(payload)


if __name__ == '__main__':
    server_class = BaseHTTPServer.HTTPServer
    httpd = server_class((HOST_NAME, PORT_NUMBER), MyHandler)
    print time.asctime(), "Server Starts - %s:%s" % (HOST_NAME, PORT_NUMBER)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    print time.asctime(), "Server Stops - %s:%s" % (HOST_NAME, PORT_NUMBER)
