""" This is the mago syntactic sugar library for MongoDB. """

# from mago.model import Model
import mago.types

# from mago.transaction import Transaction
from mago.field import Field, ReferenceField, ConstantField, EnumField, \
      FieldError
from mago.cursor import ASC, DESC
from mago.connection import connect, Session
import mago.model


Model = mago.model.Model
UnSet = mago.types.UnSetType()
version = '0.0.1~unreleased'
# __all__ = [
#     'Model', 'Field', 'ReferenceField', 'ConstantField', 'FieldError',
#     'EnumField', 'connect', 'Session', 'ASC', 'DESC', 'UnSet', 'NATIVE_TYPES',
#     'version'
# ]
