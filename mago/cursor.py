"""
Really, really basic around pymongo.Cursor. Just makes sure
that a result dict is wrapped in a Model to keep everything
clean.
"""

from pymongo.cursor import Cursor as PyCursor
from pymongo import ASCENDING as ASC
from pymongo import DESCENDING as DESC


class Cursor(PyCursor):
    """A wrapper around pymongo's Cursor class. Return model instance
    instead of dicts. It can operate with session"""

    def __init__(self, modelcls,  *args, **kwargs):
        self.session = kwargs.pop("session", None)
        self._order_entries = []
        self._modelcls = modelcls
        super().__init__(modelcls.collection(), *args, **kwargs)

    def __next__(self):
        value = super().__next__()
        return self._cast(**value)

    def __getitem__(self, index):
        value = super().__getitem__(index)
        # I hear you like cursors... so we put a cursor inside a cursor...
        if type(value) == self.__class__:   # TODO: Probably wrong!
            return value

        return self._cast(**value)

    def _cast(self, **kwargs):
        model = self._modelcls(**kwargs)
        if self.session:
            model._session = self.session
            return self.session._register_clean(model)
        return model

    def order(self, **kwargs):            # TODO: ???
        if len(kwargs) != 1:
            raise ValueError("order() requires one field = ASC or DESC.")
        for key, value in kwargs.items():
            if value not in (ASC, DESC):
                raise TypeError("Order value must be mago.ASC or mago.DESC.")
            self._order_entries.append((key, value))
            # According to the docs, only the LAST .sort() matters to
            # pymongo, so this SHOULD be safe
            self.sort(self._order_entries)
        return self
