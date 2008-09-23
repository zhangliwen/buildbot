
def load(name):
    mod = __import__(name, {}, {}, ['__all__'])
    reload(mod)
    return mod
