""" The basic field attributes. """
from collections import Callable
from bson.dbref import DBRef
from bson.objectid import ObjectId
import mago
from mago.cursor import RelationCursor


class FieldError(Exception):
    pass


class AbstractField(object):
    pass


class Field(object):
    """This class may eventually do type-checking, default values,
    etc. but for right now it's for subclassing and glorified
    documentation.
    It's a descriptor."""

    @property
    def default(self):
        if isinstance(self._default, Callable):
            return self._default()
        return self._default

    # TODO: warn about unused kwargs
    def __init__(self, value_type=None, **kwargs):
        self.value_type = value_type
        self.required = kwargs.get("required", False)
        self._default = kwargs.get("default", mago.UnSet)
        self.field_name = None

        set_cb = getattr(self, "_set_callback", None)
        get_cb = getattr(self, "_get_callback", None)
        # esta bueno! explotarlo!
        self._set_callback = kwargs.get("set_callback", set_cb)
        self._get_callback = kwargs.get("get_callback", get_cb)

    def check(self, value):
        """Checks all constraints"""
        if self.required and not value:
            raise FieldError("'{}' is required but empty.".format(
                self.field_name))

    def __set__(self, obj, val):
        if self.value_type and not isinstance(val, self.value_type):
            raise FieldError("Invalid type: {} instead of {}".format(
                type(val), self.value_type))

        if self._set_callback:
            val = self._set_callback(obj, val)
        dict.__setitem__(obj, self.field_name, val)

    def __get__(self, obj, objtype):
        # print("Field.__get__  con ", obj)
        if obj is None:
            # Classes see the descriptor itself
            return self
        if self._get_callback:
            return self._get_callback(obj, objtype)
        # return obj.get(self.field_name, NotImplemented)
        return obj.get(self.field_name, mago.UnSet)


class ReferenceField(Field):
    """ Simply holds information about the reference model. """

    def __init__(self, model, **kwargs):
        super(ReferenceField, self).__init__(model, **kwargs)
        self.model = model

    def _set_callback(self, instance, value):
        """ Resolves a Model to a DBRef """
        if value:
            value = DBRef(self.model._get_name(), value.id)
        return value

    def _get_callback(self, instance, value):
        """ Retrieves the id, then retrieves the model from the db """
        if value:
            # Should be a DBRef
            return self.model.find_one({"_id": value.id})
        return value


class ConstantField(Field):
    """ Doesn't let you change the value after setting it. """

    def __init__(self, value_type=None, **kwargs):
        super(ConstantField, self).__init__(value_type, **kwargs)

    def _set_callback(self, obj, val):
        """ Block changing values from being set. """
        if obj.id and val is not obj[self.field_name]:
            raise FieldError("Constant fields cannot be altered after saving.")
        return val

    def __delete__(self, obj):
        if obj.id:
            raise FieldError("Can not delete a constant field after saving.")


class EnumField(Field):
    """ Only accepts values from a set / list of values.
    The first argument should be an iterable with acceptable values, or
    optionally a callable that takes the instance as the first argument and
    returns an iterable with acceptable values.

    For instance, both of these are valid:

        EnumField(("a", "b", 5))

    """

    def __init__(self, iterable, **kwargs):
        super(EnumField, self).__init__(**kwargs)
        self.iterable = iterable

    def _set_callback(self, obj, val):
        """ Checks for value in iterable. """
        if val not in self.iterable:
            raise FieldError("Value {} is not acceptable.".format(val))
        return val


class RelationList(list):

    def __init__(self, model, backref, obj, iter_):
        # super(RelationList, self).__init__()
        list.__init__(self)
        # print(dir(super(RelationList, self)))

        self._model = model
        self._backref = backref
        self._obj = obj
        self.extend(iter_)

    def clear(self):
        """delete every reference from model and clear the list"""
        # TODO: delete references
        # super(RelationList, ).clear(self)
        for model in self:
            dict.__setitem__(model, self._backref, None)
        del self[:]

    def extend(self, other):
        for model in other:
            dict.__setitem__(model, self._backref, self._obj)
        # super(RelationList, ).extend(other)
        list.extend(self, other)

class OneToMany(AbstractField):

    @property
    def model(self):
        """Return related model class"""
        return mago.types.models[self._model]

    def __init__(self, model, backref):
        self.field_name = None
        self._model = model.lower()
        self._backref = backref

    def __set__(self, obj, val):
        """Done"""
        current = getattr(obj, self.field_name)
        current.clear()
        current.extend(val)

    def __get__(self, obj, objtype):
        """Done"""
        if obj is None:
            return self
        res = dict.get(obj, self.field_name, None)
        if res is None:
            res = RelationList(self.model, self._backref,
                    obj, list(self.model.collection().find({
                        self._backref : obj.id
                    })))
            dict.__setitem__(obj, self.field_name, res)

        return res

    def __delete__(self, obj):
        """Done"""
        current = getattr(obj, self.field_name)
        current.clear()


class ManyToOne(AbstractField):

    @property
    def model(self):
        return mago.types.models[self._model]

    def __init__(self, model, backref):
        self.field_name = None
        self._model = model.lower()
        self._backref = backref

    def __set__(self, obj, val):
        """Done"""
        old = dict.get(obj, self.field_name, None)
        if old:
            dict.pop(old, self._backref)
        ref = val[self._backref]
        dict.__setitem__(obj, self.field_name, val)
        ref.append(obj)

    def __get__(self, obj, objtype):
        """Done"""
        if obj is None:
            return self

        res = dict.get(obj, self.field_name, None)
        if isinstance(res, ObjectId): # wake-up!
            res = self.model.find_one({"_id": res})
            dict.__setitem__(obj, self.field_name, res)

        return res


    def __delete__(self, obj):
        old = dict.get(obj, self.field_name, None)
        if old:
            dict.pop(old, self._backref)
        dict.pop(obj, self.field_name)


class ManyToMany(object):
    _relations = []

    def __init__(self, name, modelcls, bidirectional=True):
        if name in ManyToMany._relations:
            raise ValueError("Relation name '{}' already extists".format(name))
        self._bi = bidirectional
        self._coll = mago.connection.Connection()\
          .get_collection(modelcls.__name__)

    def __set__(self, obj, val):
        raise NotImplemented("Not implemented yet")

    def __get__(self, obj, objtype):
        res = None
        if self._bi:
            res = RelationCursor({"$or" : [{ "from": obj.id}, {"to": obj.id}]})
        else:
            res = RelationCursor({"from": obj.id})
        dict.__setitem__(obj, self.field_name, res)


    def __delete__(self, obj):
        raise NotImplemented("Not implemented yet")



#
# _id | from | to
