"""Some types definitions used in mago"""
from datetime import datetime

NATIVE_TYPES = (list, dict, tuple, int, float, bool, str, datetime)

class UnSetType:
    def __bool__(self):
        return False
    def __str__(self):
        return "UnSet"
    def __repr__(self):
        return "UnSet"
