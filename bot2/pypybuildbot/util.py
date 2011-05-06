import socket

def we_are_debugging():
    return socket.gethostname() not in ("wyvern",)

def load(name):
    mod = __import__(name, {}, {}, ['__all__'])
    reload(mod)
    return mod
