from enum import auto, StrEnum


class SqlDialect(StrEnum):
    GENERIC: "SqlDialect" = auto()
    MYSQL: "SqlDialect" = auto()
    POSTGRES: "SqlDialect" = auto()
    SQLITE: "SqlDialect" = auto()
    TSQL: "SqlDialect" = auto()
