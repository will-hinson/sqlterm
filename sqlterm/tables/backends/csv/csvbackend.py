import csv
import io

from ...abstract import TableBackend
from ....sql.generic.recordset import RecordSet


class CsvBackend(TableBackend):
    def construct_table(self: "CsvBackend", record_set: RecordSet) -> str:
        output: io.StringIO = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(record_set.columns)

        for record in record_set.records:
            writer.writerow(record)

        return output.getvalue()
