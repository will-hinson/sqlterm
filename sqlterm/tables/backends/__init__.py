"""
module sqlterm.tables.backends

Contains the definitions of all supported table rendering backends
"""

from typing import Dict, Type
from ..abstract import TableBackend
from ...config import TableBackendType

from . import csv
from . import tabulate
from . import terminaltables

table_backends_by_name: Dict[TableBackendType, Type[TableBackend]] = {
    TableBackendType.CSV: csv.CsvBackend,
    TableBackendType.TABULATE: tabulate.TabulateBackend,
    TableBackendType.TERMINAL_TABLES: terminaltables.TerminalTablesBackend,
}
