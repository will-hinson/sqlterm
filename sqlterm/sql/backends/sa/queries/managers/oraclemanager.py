from typing import List, Tuple

import oracledb
from sqlalchemy import Connection

from .....exceptions import (
    RecordSetEnd,
    ReturnsNoRecords,
    SqlQueryException,
)
from .querymanager import QueryManager
from ...saquery import SaQuery


class OracleManager(QueryManager):
    __columns: List[str] | None
    __cursor: oracledb.Cursor | None
    __query_text: str
    __returned_records: bool

    def __init__(
        self: "OracleManager", connection: Connection, target_query: SaQuery, parent
    ) -> None:
        super().__init__(connection, target_query, parent)

        self.__columns = None
        self.__query_text = target_query.text
        self.__returned_records = False

        self._init_cursor()

    @property
    def columns(self: "OracleManager") -> List[str]:
        return [] if self.__columns is None else self.__columns

    def _display_dbms_output(self: "OracleManager") -> None:
        # pylint: disable=protected-access

        # get and display all dbms_output per the oracle sample
        #
        # https://github.com/oracle/python-oracledb/blob/main/samples/dbms_output.py

        get_lines_cursor: oracledb.Cursor = self.connection._dbapi_connection.cursor()

        # read ten lines at a time
        chunk_size: int = 10

        # create variables to hold the output
        lines_var: oracledb.Var = get_lines_cursor.arrayvar(str, chunk_size)
        num_lines_var: oracledb.Var = get_lines_cursor.var(int)
        num_lines_var.setvalue(0, chunk_size)

        # fetch the text that was added by PL/SQL
        while True:
            get_lines_cursor.callproc(
                "dbms_output.get_lines", (lines_var, num_lines_var)
            )
            num_lines: int = num_lines_var.getvalue()
            lines: str = lines_var.getvalue()[:num_lines]
            for line in lines:
                if line is not None:
                    self.parent.parent.print_message_sql(line)
            if num_lines < chunk_size:
                break

    def __exit__(self: "OracleManager", *_) -> None:
        if self.__cursor is not None:
            self.__cursor.close()
            self.__cursor = None

    def fetch_row(self: "OracleManager") -> Tuple:
        if not self.__returned_records:
            self.__returned_records = True
            if self.__columns is None:
                raise ReturnsNoRecords("The provided query returns no records")

        record: Tuple | None = self.__cursor.fetchone()

        if record is None:
            self._display_dbms_output()
            self.__cursor.close()
            self.__cursor = None
            raise RecordSetEnd("Reached the end of the record set")

        return record

    @property
    def has_another_record_set(self: "OracleManager") -> bool:
        self._display_dbms_output()
        return not self.__returned_records

    def _init_cursor(self: "OracleManager") -> None:
        try:
            # enable dbms output
            dbms_cursor = self.connection._dbapi_connection.cursor()
            dbms_cursor.callproc("dbms_output.enable")
            dbms_cursor.close()

            # allocate a native oracle dbapi cursor
            self.__cursor = self.connection._dbapi_connection.cursor()

            # execute the user-provided sql
            self.__cursor.execute(self.__query_text)
        except oracledb.Error as oe:
            raise SqlQueryException(": ".join(map(str, oe.args))) from oe

        # check if this query actually returns records
        if self.__cursor.description is None:
            return

        # otherwise store the result columns
        self.__columns = [column_spec[0] for column_spec in self.__cursor.description]
