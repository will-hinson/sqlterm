from typing import List, Tuple
from sqlalchemy import Connection, CursorResult
from sqlalchemy.engine import Row
from sqlalchemy.exc import StatementError

from .querymanager import QueryManager
from ...saquery import SaQuery
from .....exceptions import RecordSetEnd, ReturnsNoRecords, SqlQueryException


class DefaultManager(QueryManager):
    __cursor: CursorResult
    __columns: List[str] | None = None

    __returned_records: bool = False

    def __init__(
        self: "DefaultManager", connection: Connection, target_query: SaQuery, parent
    ) -> None:
        super().__init__(connection, target_query, parent)

        # initialize the cursor and check if it actually returns records
        try:
            self.__cursor = self.connection.execute(target_query.sa_text)
        except StatementError as se:
            self.connection.rollback()
            raise SqlQueryException("\n".join(se.args)) from se

        # store the columns that the cursor returns
        self.__columns = (
            list(self.__cursor.keys()) if self.__cursor.returns_rows else None
        )

    @property
    def columns(self: "DefaultManager") -> List[str]:
        return [] if self.__columns is None else self.__columns

    def __exit__(self: "DefaultManager", *_) -> None:
        if hasattr(self, "__cursor"):
            self.__cursor.close()

    @property
    def has_another_record_set(self: "DefaultManager") -> bool:
        return not self.__returned_records

    def fetch_row(self: "DefaultManager") -> Tuple:
        self.__returned_records = True
        if not self.__cursor.returns_rows:
            raise ReturnsNoRecords("The provided query returns no records")

        record: Row | None = self.__cursor.fetchone()

        # a null record represents the case where we've read all of the
        # results. return to the caller
        if record is None:
            raise RecordSetEnd("Reached the end of the record set")

        # pylint: disable=protected-access
        return record._tuple()
