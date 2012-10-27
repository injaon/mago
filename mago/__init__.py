""" This is the mago syntactic sugar library for MongoDB. """

from mago.model import Model, PolyModel
from mago.field import Field, ReferenceField, ConstantField, EnumField
from mago.cursor import ASC, DESC
from mago.connection import connect, session

# Allows flexible (probably dangerous) automatic field creation for
# /really/ schemaless designs.
AUTO_CREATE_FIELDS = False

__all__ = [
    'Model', 'PolyModel', 'Field', 'ReferenceField', "ConstantField",
    "EnumField", 'connect', 'session', 'ASC', 'DESC', "AUTO_CREATE_FIELDS"
]
