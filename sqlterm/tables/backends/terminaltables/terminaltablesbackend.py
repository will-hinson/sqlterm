from typing import Any

from terminaltables import SingleTable

from ...abstract import TableBackend
from ....sql.generic.recordset import RecordSet


class TerminalTablesBackend(TableBackend):
    # pylint: disable=too-few-public-methods

    def construct_table(self: "TerminalTablesBackend", record_set: RecordSet) -> str:
        table: SingleTable = SingleTable(
            [tuple([""] + record_set.columns)]
            + list(
                (
                    index,
                    *(self._field_to_str(field) for field in record),
                )
                for index, record in enumerate(record_set.records, start=1)
            )
        )
        table.inner_column_border = True
        return table.table

    def _field_to_str(self: "TerminalTablesBackend", field: Any) -> str:
        if field is not None:
            if isinstance(field, memoryview):
                return str(field.tobytes())

            return str(field)

        return "NULL"
