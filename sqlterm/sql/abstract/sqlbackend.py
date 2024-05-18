from abc import ABCMeta, abstractmethod
from typing import List, Tuple

from .query import Query
from ...tables.abstract import TableBackend
from ...prompt.dataclasses import SqlStatusDetails


class SqlBackend(metaclass=ABCMeta):
    parent: "sqlterm.SqlTerm" = None  # type: ignore
    table_backend: TableBackend | None = None

    @abstractmethod
    def connect(self: "SqlBackend", connection_string: str) -> None: ...

    @property
    @abstractmethod
    def connection_string(self: "SqlBackend") -> str: ...

    @property
    @abstractmethod
    def connected(self: "SqlBackend") -> bool: ...

    @abstractmethod
    def disconnect(self: "SqlBackend") -> None: ...

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
    def inspecting(self: "SqlBackend") -> bool: ...

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
