""" The basic field attributes. """

import warnings
from collections import Callable
from bson.dbref import DBRef


class FieldError(Exception):
    pass


class Field(object):
    """
    This class may eventually do type-checking, default values,
    etc. but for right now it's for subclassing and glorified
    documentation.
    It's a descriptor.
    """
    @property
    def default(self):
        if isinstance(self._default, Callable):
            return self._default()
        return self._default

    def __init__(self, value_type=None, **kwargs):
        self.value_type = value_type
        self.required = kwargs.get("required", False)
        self._default = kwargs.get("default", NotImplemented)
        self.field_name = None

        set_cb = getattr(self, "_set_callback", None)
        get_cb = getattr(self, "_get_callback", None)
        # esta bueno! explotarlo!
        self._set_callback = kwargs.get("set_callback", set_cb)
        self._get_callback = kwargs.get("get_callback", get_cb)

    def check(self, value):
        """Checks all constraints"""
        if self.required and value is NotImplemented:
            raise FieldError("'{}' is required but empty.".format(
                self.field_name))
        if not self.required and value is NotImplemented:
            return

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
        return obj.get(self.field_name, NotImplemented)

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
