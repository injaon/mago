""" The basic field attributes. """
from collections import Callable
from bson.dbref import DBRef
import mago
import mago.cursor


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


# Relations
class Relation(object):
    def __init__(self, name, model):
        if not issubclass(model, mago.Model):
            raise FieldError("{} must be an instance of mago.Model"
                             .format(model.__name__))
        self._model = model
        self._relation_name = "_rel_{}_{}".format(model.__name__, name)


class OneToMany(object):
    _relations = []

    def __init__(self, name, model):
        super().__init__(name, model)
        if self._relation_name in OneToMany._relations:
            raise ValueError("Relation name '{}' already extists".format(name))
        OneToMany._relations.append(self._relation_name)

    def __set__(self, obj, val):
        raise Exception("Operation not supported.")

    def __delete__(self, obj):
        """Delete _only_ the key <_relation_name> of _model"""
        if obj.session:
            raise Exception("Operation not supported.")

        self._model.collection().update(
            {self._relation_name : obj.id}, {"$unset" :
                {self._relation_name : obj.id}})

    def __get__(self, obj, objtype):
        return self._model.find({self._relation_name: obj.id},
                                session=obj.session)


class ManyToOne(object):
    def __set__(self, obj, val):
        if obj.session:
            obj.session.merge(val)

        obj[self._relation_name] = val.id

    def __get__(self, obj, objtype):
        # es un attr.
        if obj.session:
            try:
                return obj.session._pool[obj[self._relation_name]]
            except KeyError:
                # TODO: find in the session
                pass

        return self._model.find({"_id"}, obj[self._relation_name])[0]

    def __delete__(self, obj):
        del obj[self._relation_name]


class ManyToMany(object):
    _relations = []

    def __init__(self, name, modelcls):
        if name in ManyToMany._relations:
            raise ValueError("Relation name '{}' already extists".format(name))


    def __set__(self, obj, val):
        pass

    def __get__(self, obj, objtype):
        pass
