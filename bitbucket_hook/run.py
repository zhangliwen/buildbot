#!/usr/bin/python
import py
import sys
import argparse
main = py.path.local(__file__).dirpath().join('main.py').pyimport()


if __name__ == '__main__':
    HOST_NAME = 'codespeak.net'
    PORT_NUMBER = 9237
    main.app.run(
        host = HOST_NAME if 'deploy' in sys.argv else 'localhost',
        debug = 'debug' in sys.argv,
        port=PORT_NUMBER)

