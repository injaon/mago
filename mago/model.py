"""Core of the lib. It contains the class Model"""

import mago
import logging
import pickle
from mago.connection import Connection
from mago.cursor import Cursor
from mago.field import Field
from mago.decorators import notinstancemethod
from mago.types import NATIVE_TYPES
from bson.dbref import DBRef
from bson.objectid import ObjectId


def obj_to_dict(obj):
    if hasattr(obj, "to_dict"):
        return obj.to_dict()

    res = {}
    res["__class__"] = pickle.dumps(obj.__class__, 3)
    for attr in obj.__dict__:
        val = getattr(obj, attr)
        if type(val) not in NATIVE_TYPES:
            res[attr] = obj_to_dict(val)
            res[attr]["__class__"] = pickle.dumps(val.__class__, 3)
        else:
            res[attr] = val
    return res


def dict_to_obj(dic):
    class_ = dic.pop("__class__")
    res = pickle.loads(class_)()

    for attr, val in dic.items():
        if val.__class__ is dict and val.get("__class__"):
            val = dict_to_obj(val)
        setattr(res, attr, val)
    return res


class NewModelClass(type):
    """ Metaclass for inheriting field lists """
    def __new__(cls, name, bases, attributes):
        new_model = super(NewModelClass, cls).__new__(
            cls, name, bases, attributes)

        if new_model.__name__ == "Model":
            return new_model
        new_model._name = new_model.__name__.lower()

        # pre-populate fields
        new_model._fields = {}
        for attr in dir(new_model):
            value = getattr(new_model, attr)
            if not isinstance(value, Field):
                continue

            new_model._fields[attr] = value
            value.field_name = attr
        return new_model


class Entity(object):
    """It contains _only_ class methods related with the entity
    and not the object."""

    @notinstancemethod
    def remove(cls, *args, **kwargs):
        """Just a wrapper around the collection's remove."""
        if not args:
            # If you get this exception you are calling remove with no
            # arguments or with only keyword arguments, which is not
            # supported (and would remove all entries in the current
            # collection if it was.) If you really want to delete
            # everything in a collection, pass an empty dictionary like
            # Model.remove({})
            raise ValueError(
                'remove() requires a query when called with keyword arguments')
        return cls.collection().remove(*args, **kwargs)

    @notinstancemethod
    def drop(cls, *args, **kwargs):
        """ Just a wrapper around the collection's drop. """
        return cls.collection().drop(*args, **kwargs)

    @classmethod
    def update(cls, *args, **kwargs):
        """Direct passthru to PyMongo's update."""
        coll = cls.collection()
        # Maybe should do something 'clever' with the query?
        # E.g. transform Model instances to DBRefs automatically?
        return coll.update(*args, **kwargs)

    @classmethod
    def find(cls, *args, **kwargs):
        """A wrapper for the pymongo cursor. Uses all the
        same arguments."""
        if kwargs and not args:
            # If you get this exception you should probably be calling search,
            # not find. If you really want to call find, pass an empty dict:
            # Model.find({}, timeout=False)
            raise ValueError(
                'find() requires a query when called with keyword arguments')
        return Cursor(cls, *args, **kwargs)

    @classmethod
    def find_one(cls, where):
        return cls(**cls.collection().find_one(where))

    @classmethod
    def search(cls, **kwargs):
        """
        Helper method that wraps keywords to dict and automatically
        turns instances into DBRefs.
        """
        query = {}
        for key, value in kwargs.items():
            if isinstance(value, Model):
                value = value.get_ref()
            field = getattr(cls, key)

            # Try using custom field name in field.
            if field.field_name:
                key = field.field_name

            query[key] = value
        return cls.find(query)


class Model(dict, Entity, metaclass=NewModelClass):
    """Core class of the module. It is disigned to be inherited."""

    _name = None
    _collection = None
    _fields = None

    @property
    def fields(self):
        """ Property wrapper for class fields """
        return self.__class__._fields

    @property
    def id(self):
        return self.get('_id', mago.UnSet)

    @classmethod
    def collection_name(cls):
        return cls._name

    @classmethod
    def collection(cls):
        if not cls._collection:
            cls._collection = Connection.instance().get_collection(
                cls._name)
        return cls._collection

    def __init__(self, **kwargs):
        """Creates an instance of the model, without saving it."""
        super(Model, self).__init__()
        Entity.__init__(self)
        if self.__class__ is Model:
            raise TypeError("Cannot instance Model.")

        Entity.__setattr__(self, 'session', None)

        for name, field in self._fields.items():
            if field.default is not mago.UnSet:
                self[name] = field.default

        for field, value in kwargs.items():
            self[field] = value

    def save(self, *args, **kwargs):
        """Saves or updates the model in the database"""
        if self.id:
            return self.sync()
        self._check_attrs()
        store = self.copy()
        for key, val in self.items():
            if type(val) not in NATIVE_TYPES:
                store[key] = obj_to_dict(val)

        coll = self.collection()
        dict.__setitem__(self, '_id', coll.save(store, *args, **kwargs))
        return self

    def sync(self):
        """Update all the fields to the db"""
        if not self.id:
            raise ValueError("Cant sync an unsaved model.")

        self._check_attrs()
        coll = self.collection()
        doc = self.copy()
        del doc[self._id]

        # TODO: why??
        return coll.update({self._id: self.id},
                           {"$set": doc})

    def delete(self):
        """Uses the id in the collection.remove method.
        Allows all the same arguments (except the spec/id)."""
        if not self.id:
            raise ValueError('Cannot delete an unsaved model.')
        return self.collection().remove(self.id)

    def get_ref(self):
        """ Returns a DBRef for an document. """
        return DBRef(self.collection_name(), self.id)

    def _check_attrs(self, *field_names):
        """Ensures that all fields are set correctly."""
        if not field_names:
            field_names = self._fields.keys()

        declared_fields = self._fields.keys()
        for field_name in field_names:
            if field_name not in declared_fields:
                continue

            # field = getattr(self.__class__, field_name, NotImplemented)
            field = self._fields[field_name]
            value = self.get(field_name, mago.UnSet)
            field.check(value)

    # setters
    def __setattr__(self, name, value):
        if value.__class__ is dict and value.get("__class__"):
            value = dict_to_obj(value)

        if name in self._fields.keys():
            self._fields[name].__set__(self, value)
        else:
            dict.__setitem__(self, name, value)

        if Entity.__getattribute__(self, 'session'):
            Entity.__getattribute__(self, 'session')._register_dirty(self)

    def __setitem__(self, key, value):
        self.__setattr__(key, value)

    # getters
    def __getattr__(self, name):
        if name in self._fields.keys():
            return self._fields[name].__get__(self, name)
        return self.get(name, mago.UnSet)

    def __getitem__(self, key):
        return self.__getattr__(key)

    # TODO: when remove a values it changes to dirty

    # dellers
    # def __delattr__(self, name):
    #     pass

    # def __delitem__(self, key):
    #     pass

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        """
        This method compares two objects names and id values.
        If they match, they are "equal".
        """
        if not isinstance(other, Model):
            return False
        this_id = self.id
        other_id = other.id
        if self.__class__.__name__ == other.__class__.__name__ and \
                this_id and other_id and this_id == other_id:
            return True
        return False

    def __ne__(self, other):
        """ Returns the inverse of __eq__ ."""
        return not self.__eq__(other)

    def __repr__(self):
        """ Just points to __str__ """
        return str(self)

    def __str__(self):
        """str representation of the object"""
        return "<MagoModel:{} id:{}>".format(self.collection_name(), self.id)
