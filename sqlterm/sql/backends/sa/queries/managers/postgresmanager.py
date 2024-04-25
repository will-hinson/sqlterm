from typing import List, Tuple

import psycopg2
from psycopg2.extensions import cursor
from sqlalchemy import Connection
import sqlparse

from .....exceptions import RecordSetEnd, ReturnsNoRecords, SqlQueryException
from .querymanager import QueryManager
from ...saquery import SaQuery


class PostgresManager(QueryManager):
    __cursor: cursor | None = None
    __columns: List[str] | None = None

    __current_statement: int
    __statements: List[str]
    __postgres_error: bool

    def __init__(
        self: "PostgresManager", connection: Connection, target_query: SaQuery, parent
    ) -> None:
        super().__init__(connection, target_query, parent)

        self.__current_statement = 0
        self.__statements = sqlparse.split(target_query.text)
        self.__postgres_error = False

    @property
    def columns(self: "PostgresManager") -> List[str]:
        return [] if self.__columns is None else self.__columns

    def __exit__(self: "PostgresManager", *_) -> None:
        if self.__cursor is not None:
            self.__cursor.close()

        self.connection._dbapi_connection.commit()
        self.connection.commit()

    def fetch_row(self: "PostgresManager") -> Tuple:
        if self.__cursor is None:
            self._init_cursor()

        record: Tuple | None = self.__cursor.fetchone()

        if record is None:
            self.__cursor.close()
            self.__cursor = None
            raise RecordSetEnd("Reached the end of the record set")

        return record

    @property
    def has_another_record_set(self: "PostgresManager") -> bool:
        return not self.__postgres_error and self.__current_statement < len(
            self.__statements
        )

    def _init_cursor(self: "PostgresManager") -> None:
        # initialize the cursor
        try:
            self.__cursor = self.connection._dbapi_connection.cursor()
            self.__cursor.execute(self.__statements[self.__current_statement])
        except psycopg2.Error as err:
            self.__postgres_error = True
            raise SqlQueryException(err.args[0]) from err

        self.__current_statement += 1
        self._print_all_notices()

        # check if it actually returns records
        if self.__cursor.description is None:
            self.__cursor.close()

            self.__columns = None
            self.__cursor = None

            raise ReturnsNoRecords("The provided query returns no records")

        # store the result columns
        self.__columns = [column_spec[0] for column_spec in self.__cursor.description]

    def _print_all_notices(self: "PostgresManager") -> None:
        for notice_text in self.connection._dbapi_connection.notices:
            self.parent.parent.print_message_sql(notice_text)

        self.connection._dbapi_connection.notices.clear()
