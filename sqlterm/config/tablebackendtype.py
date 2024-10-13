from enum import StrEnum


class TableBackendType(StrEnum):
    CSV = "csv"
    SQLTERM_TABLES = "sqlterm_tables"
    TABULATE = "tabulate"
    TERMINAL_TABLES = "terminal_tables"
