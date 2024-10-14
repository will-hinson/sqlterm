from copy import copy
from dataclasses import dataclass
from enum import auto, Enum
import shutil
from typing import Dict, List, Tuple

from ...abstract import TableBackend
from ....sql.generic.recordset import RecordSet


class BoxCharacter(Enum):
    BOTH = auto()
    DOWNWARD = auto()
    NEITHER = auto()
    UPWARD = auto()


box_characters_by_type: Dict[BoxCharacter, str] = {
    BoxCharacter.BOTH: "┼",
    BoxCharacter.DOWNWARD: "┬",
    BoxCharacter.NEITHER: "─",
    BoxCharacter.UPWARD: "┴",
}


@dataclass
class DataColumn:
    name: str
    values: List[List[str]]
    max_length: int


@dataclass
class ColumnSpec:
    line_offset: int


class SqlTermTablesBackend(TableBackend):
    # pylint: disable=too-few-public-methods

    def _convert_record_set(
        self: "SqlTermTablesBackend", record_set: RecordSet
    ) -> List[DataColumn]:
        table_data: List[DataColumn] = []
        for index, column_name in enumerate(record_set.columns):
            table_data.append(
                DataColumn(
                    name=column_name,
                    values=(
                        values := [
                            (
                                str(record[index]).splitlines()
                                if record[index] is not None
                                else ["NULL"]
                            )
                            for record in record_set.records
                        ]
                    ),
                    max_length=max(
                        len(string_value)
                        for string_value in [column_name]
                        + [value for record in values for value in record]
                    ),
                )
            )

        return table_data

    def _render_bottom_border(
        self: "SqlTermTablesBackend",
        total_records: int,
        max_line_length: int,
        column_mappings_by_line: Dict[int, Tuple[ColumnSpec, DataColumn]],
        table_data: List[DataColumn],
    ) -> str:
        table_render: str = "\n"
        current_line_data = "╰"
        current_line_data += "─" * (len(f"{total_records + 1}") + 2)
        last_line_mappings: List[ColumnSpec] = [
            column_mapping for column_mapping, _ in column_mappings_by_line[-1]
        ]
        for data_column in table_data[-len(last_line_mappings) :]:
            current_line_data += "┴"
            current_line_data += "─" * (data_column.max_length + 2)

        current_line_data += "─" * (max_line_length - len(current_line_data))
        table_render += current_line_data + "╯"

        return table_render

    def _render_separator(
        self: "SqlTermTablesBackend",
        record_set_size: int,
        max_line_length: int,
        current_line_number: int,
        column_mappings_by_line: Dict[int, Tuple[ColumnSpec, DataColumn]],
        is_header_separator: bool,
        include_index_column: bool,
        dashed: bool = False,
    ) -> str:
        line_char: str = "─" if not dashed else "┄"

        separator_render: str
        if is_header_separator:
            separator_render = (
                "\n" + "│" + (" " * (len(f"{record_set_size + 1}") + 2)) + "├"
            )
        else:
            separator_render = (
                "\n"
                + ("├" if include_index_column else "│")
                + (line_char if include_index_column else " ")
                * (len(f"{record_set_size + 1}") + 2)
                + ("┼" if include_index_column else "├")
            )

        # determine what points need upward-facing and downward-facing box characters
        separator_line: List[BoxCharacter] = [BoxCharacter.NEITHER] * (
            max_line_length
            - len("│" + (" " * (len(f"{record_set_size + 1}") + 2)) + "├")
        )
        col_offset: int = -1
        for (
            _,
            current_line_column_data,
        ) in column_mappings_by_line[
            current_line_number
        ][:-1]:
            col_offset += current_line_column_data.max_length + 3
            separator_line[col_offset] = BoxCharacter.UPWARD

        col_offset = -1
        for (
            _,
            next_line_column_data,
        ) in column_mappings_by_line[
            current_line_number + 1
        ][:-1]:
            col_offset += next_line_column_data.max_length + 3
            if separator_line[col_offset] == BoxCharacter.UPWARD:
                separator_line[col_offset] = BoxCharacter.BOTH
            else:
                separator_line[col_offset] = BoxCharacter.DOWNWARD

        separator_render += (
            "".join(
                (
                    box_characters_by_type[char_type]
                    if not dashed
                    else box_characters_by_type[char_type].replace("─", "┄")
                )
                for char_type in separator_line
            )
            + "┤"
        )
        return separator_render

    def _render_top_border(
        self: "SqlTermTablesBackend",
        total_records: int,
        max_line_length: int,
        column_line_mappings: List[ColumnSpec],
        table_data: List[DataColumn],
    ) -> str:
        table_render: str = "╭"
        table_render += "─" * (len(f"{total_records + 1}") + 2)
        for column_mapping, data_column in zip(column_line_mappings, table_data):
            if column_mapping.line_offset > 0:
                table_render += "─" * (max_line_length - len(table_render))
                break

            table_render += "┬"
            table_render += "─" * (data_column.max_length + 2)

        table_render += "╮"
        return table_render

    def _split_column_values(
        self: "SqlTermTablesBackend", data_column: DataColumn, max_allowed_length: int
    ) -> None:
        for index, record in enumerate(copy(data_column.values)):
            split_values: List[str] = []
            for entry in record:
                if len(entry) < max_allowed_length:
                    split_values.append(entry)
                else:
                    for chunk_index in range(0, len(entry), max_allowed_length):
                        split_values.append(
                            entry[chunk_index : chunk_index + max_allowed_length]
                        )

            data_column.values[index] = split_values
            data_column.max_length = max_allowed_length

    def construct_table(self: "SqlTermTablesBackend", record_set: RecordSet) -> str:
        # get the current width of the terminal then loop over all of the values
        # and convert to strings
        terminal_width: int = shutil.get_terminal_size().columns
        table_data: List[DataColumn] = self._convert_record_set(record_set)
        total_records: int = len(record_set.records)

        # now, map all of the columns to lines
        column_line_mappings: List[ColumnSpec] = []
        column_offset: str = f"| {total_records + 1} | "
        max_line_length: int = 0
        line_number: int = 0
        for data_column in table_data:
            if data_column.max_length > (
                max_allowed_length := terminal_width - len(f"| {total_records + 1} | ")
            ):
                # split the column values up
                max_allowed_length -= 2
                self._split_column_values(data_column, max_allowed_length)

            # check if this column plus its separator can fit on this line
            if (
                len(column_offset) + len(" | ") + data_column.max_length
                > terminal_width
            ):
                max_line_length = max(max_line_length, len(column_offset) - 1)

                # start a new line
                column_offset: int = f"| {total_records + 1} | "
                line_number += 1

            column_line_mappings.append(ColumnSpec(line_offset=line_number))
            column_offset += (" " * data_column.max_length) + " | "

        max_line_length = max(max_line_length, len(column_offset) - 2)

        column_mappings_by_line: Dict[int, Tuple[ColumnSpec, DataColumn]] = {}
        for column_spec, data_column in zip(column_line_mappings, table_data):
            if column_spec.line_offset not in column_mappings_by_line:
                column_mappings_by_line[column_spec.line_offset] = []

            column_mappings_by_line[column_spec.line_offset].append(
                (column_spec, data_column)
            )
        column_mappings_by_line[-1] = column_mappings_by_line[
            max(column_mappings_by_line.keys())
        ]

        # add the first header line
        table_render: str = self._render_top_border(
            total_records, max_line_length, column_line_mappings, table_data
        )

        # now, add in each row of columns
        current_line_data: str = ""
        current_line_number: int = -1
        columns_are_multiline: bool = False
        for column_mapping, data_column in zip(column_line_mappings, table_data):
            if column_mapping.line_offset != current_line_number:
                # only run against the first actual line. this allows the new line code below to run
                # first and set things up
                if current_line_number >= 0:
                    current_line_data += (
                        " " * (max_line_length - len(current_line_data) + 1) + "│"
                    )
                    table_render += current_line_data + self._render_separator(
                        total_records,
                        max_line_length,
                        current_line_number,
                        column_mappings_by_line,
                        is_header_separator=True,
                        include_index_column=False,
                        dashed=True,
                    )
                    columns_are_multiline = True

                current_line_number += 1
                current_line_data = ""
                current_line_data += (
                    "\n" + "│" + (" " * (len(f"{total_records + 1}") + 2))
                )

            current_line_data += (
                "│ "
                + (
                    data_column.name
                    + " " * (data_column.max_length - len(data_column.name))
                )
                + " "
            )

        # append the final line of columns
        table_render += (
            current_line_data
            + (" " * (max_line_length - len(current_line_data) + 1))
            + "│"
        )

        # render the line separating the headers from the data
        table_render += self._render_separator(
            total_records,
            max_line_length,
            -1,
            column_mappings_by_line,
            is_header_separator=False,
            include_index_column=True,
        )

        # now, render all the records
        max_line_number: int = max(
            mapping.line_offset for mapping in column_line_mappings
        )
        for index in range(total_records):
            # render the index column
            current_line_data: str = (
                f"\n│ {str(index + 1).rjust(len(str(total_records)))} "
            )
            current_line_number: int = 0

            # loop over all of the virtual line numbers
            while current_line_number <= max_line_number:
                # find the highest offset for this column group
                highest_line_offset: int = 0
                for _, data_column in column_mappings_by_line[current_line_number]:
                    highest_line_offset = max(
                        highest_line_offset, len(data_column.values[index]) - 1
                    )

                # loop over and build the output line by line
                for physical_line_offset in range(highest_line_offset + 1):
                    for _, data_column in column_mappings_by_line[current_line_number]:
                        if physical_line_offset < len(data_column.values[index]):
                            current_line_data += (
                                "│ "
                                + data_column.values[index][physical_line_offset].ljust(
                                    data_column.max_length
                                )
                                + " "
                            )
                        else:
                            current_line_data += f"│ {' ' * data_column.max_length} "

                    current_line_data += (
                        " " * (max_line_length - len(current_line_data) + 1)
                    ) + "│"
                    table_render += current_line_data
                    current_line_data = ""
                    current_line_data += f"\n│ {" " * len(str(total_records))} "

                if current_line_number < max(column_mappings_by_line.keys()):
                    table_render += self._render_separator(
                        total_records,
                        max_line_length,
                        current_line_number,
                        column_mappings_by_line,
                        is_header_separator=False,
                        include_index_column=False,
                        dashed=True,
                    )

                current_line_number += 1

            if columns_are_multiline and index < total_records - 1:
                table_render += self._render_separator(
                    total_records,
                    max_line_length,
                    -1,
                    column_mappings_by_line,
                    is_header_separator=False,
                    include_index_column=True,
                )

        # add the footer line
        table_render += self._render_bottom_border(
            total_records, max_line_length, column_mappings_by_line, table_data
        )

        # SELECT TOP 2 * FROM INFORMATION_SCHEMA.TABLES;
        """
        SELECT '  some
value' AS "a
column", 2 AS b;
        """

        return table_render
