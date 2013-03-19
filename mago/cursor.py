"""
Really, really basic around pymongo.Cursor. Just makes sure
that a result dict is wrapped in a Model to keep everything
clean.
"""

from pymongo.cursor import Cursor as PyCursor
from pymongo import ASCENDING as ASC
from pymongo import DESCENDING as DESC


def cast(modelcls, session, **doc):
    model = modelcls(**doc)
    if session:
        model._session = session
        return session._register_clean(model)   # TODO: WTF!?
    return model



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
        return cast(**value)

    def __getitem__(self, index):
        value = super().__getitem__(index)
        # I hear you like cursors... so we put a cursor inside a cursor...
        if type(value) == self.__class__:   # TODO: Probably wrong!
            return value

        return cast(**value)

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


class RelationCursor(Cursor):
    def __init__(self, obj, related, bidirectional, *args, **kwargs):
        super().__init__(related.collection(), *args, **kwargs)
        self._obj = obj
        self._relatedcls = related
        self._bi = bidirectional
        self._added = []

    def __next__(self):
        value = super().__next__()
        value = value["from"] if value["to"] == self._obj.id else value["to"]
        return cast(self._relatedcls, self._obj._session,
                    **self._relatedcls.find_one({"_id": value}))

    def __getitem__(self, index):
        value = super().__getitem__(index)
        value = value["from"] if value["to"] == self._obj.id else value["to"]
        return cast(self._relatedcls, self._obj._session,
                    **self._relatedcls.find_one({"_id": value}))

    def append(self, model):
        if self._obj._session:
            obj._session.add_operation(self._coll.insert,
                                       {"from": self._obj.id,"to": model.id})
            self._obj._session.add(model)
        else:
            self._coll.insert({"from": self._obj.id,"to": model.id})
        self._added.append(model)

    def order(self):
        raise NotImplemented("Not implemented yet")
#
