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
    def columns(self: "QueryManager") -> List[str]:
        """
        Returns a list of names that represent the fields contained within the
        currently selected result set.

        Args:
            None

        Returns:
            List[str]: The list of column names

        Raises:
            Nothing. If there are no columns, an empty list will be returned
        """

    @property
    def connection(self: "QueryManager") -> Connection:
        """
        Returns the SQLAlchemy connection that is wrapped by this manager.

        Args:
            None

        Returns:
            Connection: This manager's SQLAlchemy connection instance

        Raises:
            Nothing
        """

        return self.__connection

    def __enter__(self: "QueryManager") -> "QueryManager":
        return self

    @abstractmethod
    def __exit__(self: "QueryManager", exc_type, exc_value, traceback) -> None: ...

    @abstractmethod
    def fetch_row(self: "QueryManager") -> Tuple:
        """
        Fetches a record from the current result set if one is available.

        Args:
            None

        Returns:
            Tuple: A set of values representing the fields of the record.
                These can be mapped to column names using the columns property

        Raises:
            RecordSetEnd: If the end of the record set has been reached
        """

    @property
    @abstractmethod
    def has_another_record_set(self: "QueryManager") -> bool:
        """
        Returns a boolean value representing whether or not this manager has
        another record set to return from the currently executing query.

        Args:
            None

        Returns:
            bool: True if there is another result set to be read and False if
                all record sets have been read for the current query
        """

    @property
    def parent(self: "QueryManager") -> "sabackend.SaBackend":
        """
        Gets the SQLAlchemy SABackend instance that created this QueryManager

        Args:
            None

        Returns:
            SABackend: The SQLAlchemy backend instance that created this QueryManager

        Raises:
            Nothing
        """

        return self.__parent

    @property
    def target_query(self: "QueryManager") -> SaQuery:
        """
        Returns the SQLAlchemy query instance that this QueryManager is executing.

        Args:
            None

        Returns:
            SAQuery: The query that this manager is executing

        Raises:
            Nothing
        """

        return self.__target_query


# pylint: disable=wrong-import-position
from ... import sabackend
