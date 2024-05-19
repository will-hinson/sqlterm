from abc import ABCMeta, abstractmethod
from typing import Any, Iterable, List


from ..dataclasses import InputModel, SqlReference
from ...sql.generic.dataclasses import SqlStructure
from ...sql.generic.enums import SqlDialect
from ...config import SqlTermConfig


class PromptBackend(metaclass=ABCMeta):
    config: SqlTermConfig
    _dialect: SqlDialect
    parent: "sqlterm.SqlTerm"

    def __init__(self: "PromptBackend", config: SqlTermConfig) -> None:
        self.config = config
        self._dialect = SqlDialect.GENERIC

    @abstractmethod
    def change_dialect(self: "PromptBackend", dialect: SqlDialect) -> None: ...

    @abstractmethod
    def clear_completions(self: "PromptBackend") -> None: ...

    @property
    def dialect(self: "PromptBackend") -> SqlDialect:
        return self._dialect

    @abstractmethod
    def display_exception(
        self: "PromptBackend", exception: Exception, unhandled: bool = False
    ) -> None: ...

    @abstractmethod
    def display_info(self: "PromptBackend", info: str) -> None: ...

    @abstractmethod
    def display_message_sql(self: "PromptBackend", message: str) -> None: ...

    @abstractmethod
    def display_object_browser(
        self: "PromptBackend", show_loading: bool
    ) -> SqlReference | None: ...

    @abstractmethod
    def display_progress(
        self: "PromptBackend", *progress_messages: List[str]
    ) -> None: ...

    @abstractmethod
    def display_table(self: "PromptBackend", table: str) -> None: ...

    @abstractmethod
    def get_command(self: "PromptBackend", initial_input: str | None = None) -> str: ...

    @abstractmethod
    def hide_cursor(self: "PromptBackend") -> None: ...

    @abstractmethod
    def prompt_for(
        self: "PromptBackend", prompt_series: Iterable[InputModel]
    ) -> List[Any]: ...

    @abstractmethod
    def refresh_structure(self: "PromptBackend", structure: SqlStructure) -> None: ...

    @abstractmethod
    def show_cursor(self: "PromptBackend") -> None: ...


# pylint: disable=wrong-import-position
from ... import sqlterm
