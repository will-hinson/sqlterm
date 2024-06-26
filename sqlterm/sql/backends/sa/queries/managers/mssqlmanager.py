from enum import IntEnum
from typing import List, Tuple

import pyodbc
from sqlalchemy import Connection
from sqlalchemy.engine import URL

from .....exceptions import (
    RecordSetEnd,
    ReturnsNoRecords,
    SqlQueryException,
)
from .querymanager import QueryManager
from ...saquery import SaQuery

# NOTE: disabling this as pylint is unhappy about pyodbc
# pylint: disable=c-extension-no-member


class _MsSqlErrorNumbers(IntEnum):
    CHANGE_DATABASE = 5701


class MsSqlManager(QueryManager):
    __cursor: pyodbc.Cursor | None = None
    __columns: List[str] | None = None

    __query: str
    __mssql_error: bool

    __rows_fetched: bool = False

    def __init__(
        self: "MsSqlManager",
        connection: Connection,
        target_query: SaQuery,
        parent,
    ) -> None:
        super().__init__(connection, target_query, parent)

        self.__query = target_query.text
        self.__mssql_error = False

        try:
            self._init_cursor()
        except (pyodbc.Error, pyodbc.OperationalError) as pe:
            raise SqlQueryException(self._message_for_pyodbc_error(pe)) from pe

    @property
    def columns(self: "MsSqlManager") -> List[str]:
        return [] if self.__columns is None else self.__columns

    def __exit__(self: "MsSqlManager", *_) -> None:
        if self.__cursor is not None:
            self.__cursor.close()

    def fetch_row(self: "MsSqlManager") -> Tuple:
        self.__rows_fetched = True
        if self.__cursor.description is None:
            raise RecordSetEnd("Reached the end of the record set")

        record: Tuple | None = self.__cursor.fetchone()

        if record is None:
            raise RecordSetEnd("Reached the end of the record set")

        return record

    @property
    def has_another_record_set(self: "MsSqlManager") -> bool:
        self._print_all_messages()

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

        return not self.__mssql_error and cursor_has_records

    def _init_cursor(self: "MsSqlManager") -> None:
        # initialize the cursor
        try:
            self.__cursor = self.connection._dbapi_connection.cursor().execute(
                self.__query
            )
        except pyodbc.Error as pe:
            self.__mssql_error = True

            raise SqlQueryException(self._message_for_pyodbc_error(pe)) from pe

    def _inspect_message(
        self: "MsSqlManager", message_code: str, message_text: str
    ) -> None:
        # remove the extraneous detail from the message code and try parsing to an int
        message_code_int: int
        try:
            message_code_int = int(
                message_code[message_code.index("(") + 1 :][:-1].strip()
            )
        except ValueError:
            # give up if we couldn't parse the message code out
            return

        # strip the prefix from the incoming message
        message_text = self._remove_message_prefix(message_text)

        self._inspect_message_for_code(message_code_int, message_text)

    def _inspect_message_for_code(
        self: "MsSqlManager", message_code: int, message_text: str
    ) -> None:
        match message_code:
            case _MsSqlErrorNumbers.CHANGE_DATABASE:
                # extract the new database name from the message text
                message_text = message_text[message_text.index("'") + 1 :]
                message_text = message_text[: message_text.rfind("'.")]

                # change the selected database in the connection url
                self.parent.engine.url = URL.create(
                    database=message_text,
                    **{
                        key: value
                        for key, value in self.parent.engine.url._asdict().items()
                        if key != "database"
                    },
                )
            case _:
                ...

    def _message_for_pyodbc_error(self: "MsSqlManager", error: pyodbc.Error) -> str:
        # extract the actual error message from the exception. we remove the initial
        # prefix with the driver details
        error_message: str = error.args[1]
        error_message = error_message[error_message.index(" ") :].strip()
        error_message = self._remove_message_prefix(error_message)

        # remove the function name postfix
        error_message = error_message[: error_message.rfind("(")].strip()

        return f"[{error.args[0]}] {error_message}"

    def _next_record_set(self: "MsSqlManager") -> bool:
        self._print_all_messages()

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

    def _print_all_messages(self: "MsSqlManager") -> None:
        for message_code, message_text in self.__cursor.messages:
            # strip the extraneous prefix from the incoming message
            message_text = self._remove_message_prefix(message_text)

            # inspect the message to see if it contains something pertinent
            self._inspect_message(message_code, message_text)

            # display the message
            self.parent.parent.print_message_sql(message_text)

        self.__cursor.messages.clear()

    def _remove_message_prefix(self: "MsSqlManager", message: str) -> str:
        # there are three prefixes to remove from an odbc message
        for _ in range(3):
            if "]" not in message:
                break

            message = message[message.index("]") + 1 :]

        return message

    def _try_populate_columns(self: "MsSqlManager") -> None:
        if self.__cursor.description is not None:
            self.__columns = [
                column_spec[0] for column_spec in self.__cursor.description
            ]
        else:
            self.__columns = None
