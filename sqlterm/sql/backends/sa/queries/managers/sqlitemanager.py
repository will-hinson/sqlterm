import sqlite3
from typing import List, Tuple

from sqlalchemy import Connection
import sqlparse

from .....exceptions import RecordSetEnd, ReturnsNoRecords, SqlQueryException
from .querymanager import QueryManager
from ...saquery import SaQuery


class SqliteManager(QueryManager):
    __cursor: sqlite3.Cursor | None = None
    __columns: List[str] | None = None

    __current_statement: int
    __statements: List[str]
    __sqlite_error: bool

    def __init__(
        self: "SqliteManager", connection: Connection, target_query: SaQuery, parent
    ) -> None:
        super().__init__(connection, target_query, parent)

        self.__current_statement = 0
        self.__statements = sqlparse.split(target_query.text)
        self.__sqlite_error = False

    @property
    def columns(self: "SqliteManager") -> List[str]:
        return [] if self.__columns is None else self.__columns

    def __exit__(self: "SqliteManager", *_) -> None:
        if self.__cursor is not None:
            self.__cursor.close()

        self.connection._dbapi_connection.commit()
        self.connection.commit()

    def fetch_row(self: "SqliteManager") -> Tuple:
        if self.__cursor is None:
            self._init_cursor()

        record: Tuple | None = self.__cursor.fetchone()

        if record is None:
            self.__cursor.close()
            self.__cursor = None
            raise RecordSetEnd("Reached the end of the record set")

        return record

    @property
    def has_another_record_set(self: "SqliteManager") -> bool:
        return not self.__sqlite_error and self.__current_statement < len(
            self.__statements
        )

    def _init_cursor(self: "SqliteManager") -> None:
        # pylint: disable=protected-access

        # initialize the cursor
        try:
            self.__cursor = self.connection._dbapi_connection.cursor().execute(
                self.__statements[self.__current_statement]
            )
        except sqlite3.OperationalError as oe:
            self.__sqlite_error = True
            raise SqlQueryException(
                f"[{oe.sqlite_errorname}] "
                + "\n".join(oe.args)
                + f" ({oe.sqlite_errorcode})"
            ) from oe

        self.__current_statement += 1

        # check if it actually returns records
        if self.__cursor.description is None:
            self.__cursor.close()
            self.__cursor = None
            raise ReturnsNoRecords("The provided query returns no records")

        # store the result columns
        self.__columns = [column_spec[0] for column_spec in self.__cursor.description]
