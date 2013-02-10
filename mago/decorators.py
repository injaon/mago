# import mago
"""Just various decorators."""


class notinstancemethod(object):
    """Used to refuse access to a classmethod if called from an instance."""
    def __init__(self, func):
        self.func = classmethod(func)

    def __get__(self, obj, objtype=None):
        if obj is not None:
            raise TypeError("Cannot call this method on an instance.")
        return self.func.__get__(obj, objtype)


def register_dirty(func):
    def _register(self, name, *args, **kwargs):
        old = self.get(name, mago.UnSet)
        res = func(self, name, *args, **kwargs)

        if old != self.get(name, mago.UnSet) and self.session \
          and self.session.is_active:
            self.session._register_change(self, name, old)
        return res
    return _register


def singleton(cls):
    """This Class decorator implements the Singleton design pattern."""
    instances = {}

    def instance():
        if cls not in instances:
            instances[cls] = cls()
        return instances[cls]
    return instance
