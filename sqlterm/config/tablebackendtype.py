from enum import StrEnum


class TableBackendType(StrEnum):
    CSV = "csv"
    TABULATE = "tabulate"
    TERMINAL_TABLES = "terminal_tables"
