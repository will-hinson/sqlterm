from tabulate import tabulate

from ...abstract import TableBackend
from ....sql.generic.recordset import RecordSet


class TabulateBackend(TableBackend):
    def construct_table(self: "TabulateBackend", record_set: RecordSet) -> str:
        return tabulate(
            record_set.records,
            headers=record_set.columns,
            showindex=range(1, len(record_set.records) + 1),
            tablefmt="rounded_outline",
        )
