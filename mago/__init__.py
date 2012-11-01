""" This is the mago syntactic sugar library for MongoDB. """

from mago.model import Model
from mago.field import Field, ReferenceField, ConstantField, EnumField, FieldError
from mago.cursor import ASC, DESC
from mago.connection import connect, session
from mago.types import NATIVE_TYPES, UnSetType

# Allows flexible (probably dangerous) automatic field creation for
# /really/ schemaless designs.
AUTO_CREATE_FIELDS = False

UnSet = UnSetType()

__all__ = [
    'Model', 'Field', 'ReferenceField', "ConstantField", "FieldError",
    "EnumField", 'connect', 'session', 'ASC', 'DESC', "AUTO_CREATE_FIELDS",
    "UnSet", "NATIVE_TYPES"
]
