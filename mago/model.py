"""Core of the lib. It contains the class Model"""

import mago
import logging
import pickle
import mago.connection
import mago.cursor
import mago.field
import mago.decorators
import mago.types
from bson.dbref import DBRef
from bson.objectid import ObjectId


def obj_to_dict(obj):
    """Translate a non-model and non-native object to dict"""
    if hasattr(obj, "to_dict"):
        return obj.to_dict()

    res = {}
    res["__class__"] = pickle.dumps(obj.__class__, 3)
    for attr in obj.__dict__:
        val = getattr(obj, attr)
        if type(val) not in mago.types.NATIVE:
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
        mago.types.models[new_model._name] = new_model

        # pre-populate fields
        new_model._fields = {}
        for attr in dir(new_model):
            value = getattr(new_model, attr)
            if not isinstance(value, mago.field.Field):
                continue

            new_model._fields[attr] = value
            value.field_name = attr
        return new_model


class Entity(object):
    """It contains _only_ class methods related with the entity
    and not the object."""

    @mago.decorators.notinstancemethod
    def drop(cls, *args, **kwargs):
        """ Just a wrapper around the collection's drop. """
        return cls.collection().drop(*args, **kwargs)

    @classmethod
    def find(cls, *args, **kwargs):
        """A wrapper for the pymongo cursor. Uses all the same arguments."""
        if kwargs and not args:
            # If you get this exception you should probably be calling search,
            # not find. If you really want to call find, pass an empty dict:
            # Model.find({}, timeout=False)
            raise ValueError(
                'find() requires a query when called with keyword arguments')
        return mago.cursor.Cursor(cls, *args, **kwargs)

    @classmethod
    def find_one(cls, where):
        doc = cls.collection().find_one(where)
        return cls(**doc) if doc else None

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
            cls._collection = mago.connection.Connection()\
              .get_collection(cls._name)
        return cls._collection

    def __init__(self, **kwargs):
        """Creates an instance of the model, without saving it."""
        # TODO: change DBRef for instances
        dict.__init__(self)
        Entity.__init__(self)
        if self.__class__ is Model:
            raise TypeError("Cannot instance Model.")

        self._session = None
        self._state = None
        for name, field in self._fields.items():
            if field.default is not mago.UnSet:
                self[name] = field.default

        for field, value in kwargs.items():
            self[field] = value

        if not '_id' in self:
            dict.__setitem__(self,'_id', ObjectId())
        if not '_trans' in self:
            dict.__setitem__(self,'_trans', [])

    def save(self, *args, **kwargs):
        """Saves the model in the database"""
        self._check_attrs()
        store = self.copy()
        for key, val in self.items():
            if type(val) not in mago.types.NATIVE:
                store[key] = obj_to_dict(val)

        self.collection().save(store, *args, **kwargs)
        return self

    def sync(self):
        """Update all the fields to the db"""
        self._check_attrs()
        doc = self.copy()
        del doc["_id"]
        return self.collection().update({'_id': self.id},
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
    @mago.decorators.track_changes
    def __setitem__(self, key, value):
        if value.__class__ is dict and value.get("__class__"):
            value = dict_to_obj(value)

        if key in self._fields.keys():
            self._fields[key].__set__(self, value)
        else:
            dict.__setitem__(self, key, value)

    def __getitem__(self, key):
        if key in self._fields.keys():
            return self._fields[key].__get__(self, key)
        return self.get(key, mago.UnSet)

    # dellers
    @mago.decorators.track_changes
    def __delitem__(self, key):           # TODO: del model.id ??
        if key == "_id":
            raise KeyError("You cannot delete a model's `id`")
        dict.__delitem__(self, key)

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        """Compares two objects names and id values. If they match,
         they are "equal"."""
        if not isinstance(other, Model):
            return False
        this_id = self.id
        other_id = other.id
        if self.__class__ is other.__class__ and \
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
