from enum import auto, StrEnum


class SqlObjectType(StrEnum):
    CATALOG = auto()
    COLUMN = auto()
    DATABASE = auto()
    DATATYPE_BUILTIN = auto()
    DATATYPE_USER = auto()
    FUNCTION = auto()
    FUNCTION_TABLE_VALUED = auto()
    FUNCTION_SCALAR = auto()
    KEYWORD = auto()
    PARAMETER = auto()
    PRAGMA = auto()
    PROCEDURE = auto()
    SCHEMA = auto()
    SYNONYM = auto()
    TABLE = auto()
    VIEW = auto()
