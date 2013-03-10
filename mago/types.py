"""Some types definitions used in mago"""
from datetime import datetime
from bson.objectid  import ObjectId

NATIVE = (list, dict, tuple, int, float, bool, str, datetime, ObjectId)

class UnSetType:
    def __bool__(self):
        return False
    def __str__(self):
        return "UnSet"
    def __repr__(self):
        return "UnSet"
