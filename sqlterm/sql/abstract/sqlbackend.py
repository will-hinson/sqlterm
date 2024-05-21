from abc import ABCMeta, abstractmethod
from typing import List, Tuple

from .query import Query
from ...tables.abstract import TableBackend
from ...prompt.dataclasses import SqlStatusDetails


class SqlBackend(metaclass=ABCMeta):
    parent: "sqlterm.SqlTerm" = None  # type: ignore
    table_backend: TableBackend | None = None

    @abstractmethod
    def connect(self: "SqlBackend", connection_string: str) -> None:
        """
        Establishes a connection on this SqlBackend type using the provided connection
        string. Nothing is returned and the connection state is stored internally.

        Args:
            connection_string (str): A string that can be resolved into a connection.
                This can include aliases, dialect names, and fully qualified connection
                specifications.

        Returns:
            Nothing. The connection string is stored internally.

        Raises:
            SqlConnectionException: If there is an issue connecting using the provided
                connection string
        """

    @property
    @abstractmethod
    def connection_string(self: "SqlBackend") -> str:
        """
        Returns the connection string that was used to initialize the current SQL
        session if a session exists. Otherwise, raises an exception to indicate
        that no session exists.

        Args:
            None

        Returns:
            str: The connection string used to establish the current SQL session

        Raises:
            DisconnectedException: If a SQL session is not currently established
        """

    @property
    @abstractmethod
    def connected(self: "SqlBackend") -> bool:
        """
        Returns a boolean value representing whether or not this SqlBackend currently
        has an established SQL connection.

        Args:
            None

        Returns:
            bool: Representing whether or not this SQL backend is currently connection

        Raises:
            Nothing
        """

    @abstractmethod
    def disconnect(self: "SqlBackend") -> None:
        """
        Disconnects any current SQL session established by this SqlBackend.

        Args:
            None

        Returns:
            Nothing

        Raises:
            Nothing
        """

    @abstractmethod
    def display_progress(self: "SqlBackend", *progress_messages: str) -> None: ...

    @abstractmethod
    def execute(self: "SqlBackend", query: Query) -> None: ...

    @abstractmethod
    def fetch_results_for(self: "SqlBackend", query: Query) -> List[Tuple]: ...

    @abstractmethod
    def get_status(self: "SqlBackend") -> SqlStatusDetails: ...

    @abstractmethod
    def invalidate_completions(self: "SqlBackend") -> None: ...

    @property
    @abstractmethod
    def inspecting(self: "SqlBackend") -> bool:
        """
        Returns a boolean value representing whether or not this SqlBackend is
        currently in the process of inspecting the remote server it is connected to.

        Args:
            None

        Returns:
            bool: Representing whether or not this SqlBackend is currently inspecting
                a remote SQL server

        Raises:
            Nothing
        """

    @abstractmethod
    def make_query(self: "SqlBackend", query_str: str) -> Query: ...

    @abstractmethod
    def required_packages_for_dialect(
        self: "SqlBackend", dialect: str
    ) -> List[str]: ...

    @abstractmethod
    def resolve_connection_string(
        self: "SqlBackend", connection_string: str, test_connection: bool = False
    ) -> str: ...


# pylint: disable=wrong-import-position
from ... import sqlterm
