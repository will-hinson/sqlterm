from typing import List, Tuple

from mysql.connector.errors import Error
from mysql.connector.cursor_cext import CMySQLCursorBuffered
from sqlalchemy import Connection

from .....exceptions import RecordSetEnd, ReturnsNoRecords, SqlQueryException
from .querymanager import QueryManager
from ...saquery import SaQuery


class MySqlManager(QueryManager):
    __columns: List[str] | None = None
    __cursor: CMySQLCursorBuffered | None = None
    __mysql_error: bool = False
    __rows_fetched: bool = False

    def __init__(
        self: "MySqlManager", connection: Connection, target_query: SaQuery, parent
    ) -> None:
        super().__init__(connection, target_query, parent)

        self._init_cursor()

    @property
    def columns(self: "MySqlManager") -> List[str]:
        return [] if self.__columns is None else self.__columns

    def __exit__(self: "MySqlManager", *_) -> None:
        if self.__cursor is not None:
            self.__cursor.close()

    def fetch_row(self: "MySqlManager") -> Tuple:
        self.__rows_fetched = True
        if self.__cursor.description is None:
            raise RecordSetEnd("Reached the end of the record set")

        record: Tuple | None = self.__cursor.fetchone()

        if record is None:
            raise RecordSetEnd("Reached the end of the record set")

        return record

    @property
    def has_another_record_set(self: "MySqlManager") -> bool:
        cursor_has_records: bool = True

        if self.__rows_fetched:
            # if we've already fetch one record set, advance until we find another one with records
            found_real_result: bool = False
            while not found_real_result:
                try:
                    cursor_has_records = self._next_record_set()
                    found_real_result = True
                except ReturnsNoRecords:
                    ...
        else:
            # otherwise, try populating columns for this result
            self._try_populate_columns()

        return not self.__mysql_error and cursor_has_records

    def _init_cursor(self: "MySqlManager") -> None:
        try:
            self.__cursor = self.connection._dbapi_connection.cursor()
            self.__cursor.execute(self.target_query.text)
        except Error as err:
            self.__mysql_error = True
            raise SqlQueryException(err.args[1]) from err

    def _next_record_set(self: "MySqlManager") -> bool:
        # try to advance to the next record set
        result: bool | None = self.__cursor.nextset()
        if not result:
            # the cursor has no more record sets. return false to signify this state
            return False

        # check if this record set actually returns records
        if self.__cursor.description is None:
            raise ReturnsNoRecords("The current result set returns no records")

        self._populate_columns()
        return True

    def _populate_columns(self: "MsSqlManager") -> None:
        self.__columns = [column_spec[0] for column_spec in self.__cursor.description]

    def _try_populate_columns(self: "MsSqlManager") -> None:
        if self.__cursor.description is not None:
            self.__columns = [
                column_spec[0] for column_spec in self.__cursor.description
            ]
        else:
            self.__columns = None
