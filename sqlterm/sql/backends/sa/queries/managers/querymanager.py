from abc import ABCMeta, abstractmethod
from typing import List, Tuple

from sqlalchemy import Connection

from ...saquery import SaQuery


class QueryManager(metaclass=ABCMeta):
    __connection: Connection
    __parent: "sabackend.SaBackend"
    __target_query: SaQuery

    def __init__(
        self: "QueryManager",
        connection: Connection,
        target_query: SaQuery,
        parent: "sabackend.SaBackend",
    ) -> None:
        self.__connection = connection
        self.__parent = parent
        self.__target_query = target_query

    @property
    @abstractmethod
    def columns(self: "QueryManager") -> List[str]: ...

    @property
    def connection(self: "QueryManager") -> Connection:
        return self.__connection

    def __enter__(self: "QueryManager") -> "QueryManager":
        return self

    @abstractmethod
    def __exit__(self: "QueryManager", exc_type, exc_value, traceback) -> None: ...

    @abstractmethod
    def fetch_row(self: "QueryManager") -> Tuple | None: ...

    @property
    @abstractmethod
    def has_another_record_set(self: "QueryManager") -> bool: ...

    @property
    def parent(self: "QueryManager") -> "sabackend.SaBackend":
        return self.__parent

    @property
    def target_query(self: "QueryManager") -> SaQuery:
        return self.__target_query


# pylint: disable=wrong-import-position
from ... import sabackend
