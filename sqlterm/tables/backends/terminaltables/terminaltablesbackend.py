from terminaltables import SingleTable

from ...abstract import TableBackend
from ....sql.generic.recordset import RecordSet


class TerminalTablesBackend(TableBackend):
    def construct_table(self: "TerminalTablesBackend", record_set: RecordSet) -> str:
        table: SingleTable = SingleTable(
            [tuple([""] + record_set.columns)]
            + list(
                (
                    index,
                    *(str(field) if field is not None else "NULL" for field in record),
                )
                for index, record in enumerate(record_set.records, start=1)
            )
        )
        table.inner_column_border = True
        return table.table
