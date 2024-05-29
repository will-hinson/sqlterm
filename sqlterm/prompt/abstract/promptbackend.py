"""
module sqlterm.prompt.abstract.promptbackend

Contains the definition of the PromptBackend class, an abstract base class that
is extended by all sqlterm prompt integrations (i.e., prompt_toolkit)
"""

from abc import ABCMeta, abstractmethod
from typing import Any, Iterable, List, Type


from ..dataclasses import InputModel, SqlReference
from ...sql.generic.dataclasses import SqlStructure
from ...sql.generic.enums import SqlDialect
from ...config import SqlTermConfig


class PromptBackend(metaclass=ABCMeta):
    """
    class PromptBackend

    Abstract base class that is extended by all sqlterm prompt
    integrations (i.e., prompt_toolkit)
    """

    config: SqlTermConfig
    _dialect: SqlDialect
    parent: "sqlterm.SqlTerm"

    def __init__(self: "PromptBackend", config: SqlTermConfig) -> None:
        self.config = config
        self._dialect = SqlDialect.GENERIC

    @abstractmethod
    def add_style(self: "PromptBackend", name: str, style_class: Type) -> None: ...

    @abstractmethod
    def change_dialect(self: "PromptBackend", dialect: SqlDialect) -> None:
        """
        Changes the current dialect that this prompt backend is utilizing
        when prompting the user.

        Args:
            dialect (SqlDialect): The abstract SqlDialect to switch to

        Returns:
            Nothing

        Raises:
            Exception: Client classes may raise exceptions
        """

    @abstractmethod
    def clear_completions(self: "PromptBackend") -> None:
        """
        Clears any current completion options stored in this prompt backend

        Args:
            None

        Returns:
            Nothing

        Raises:
            Nothing
        """

    @property
    def dialect(self: "PromptBackend") -> SqlDialect:
        """
        Returns the current SQL dialect this prompt backend is using

        Args:
            None

        Returns:
            SqlDialect: The current SQL dialect in use by this prompt backend

        Raises:
            Nothing
        """

        return self._dialect

    @abstractmethod
    def display_exception(
        self: "PromptBackend", exception: Exception, unhandled: bool = False
    ) -> None:
        """
        Displays an exception that occurred during command or query
        exception to the user

        Args:
            exception (Exception): The exception to display
            unhandled (bool): Represents whether or not the exception
                was considered unhandled. A full traceback will be
                displayed in the exception was unhandled

        Returns:
            None

        Raises:
            Nothing
        """

    @abstractmethod
    def display_info(self: "PromptBackend", info: str) -> None:
        """
        Displays an informational message to the user

        Args:
            info (str): The message to be displayed

        Returns:
            None

        Raises:
            Nothing
        """

    @abstractmethod
    def display_message_sql(self: "PromptBackend", message: str) -> None:
        """
        Displays an informational message to the user

        Args:
            info (str): The message to be displayed

        Returns:
            None

        Raises:
            Nothing
        """

    @abstractmethod
    def display_object_browser(
        self: "PromptBackend", show_loading: bool
    ) -> SqlReference | None:
        """
        Displays an object browser to the user where they can select a
        SQL object

        Args:
            show_loading (bool): Whether or not the object browser should
                show some indication of loading

        Returns:
            SqlReference | None: An optional SQL object if the user selected one

        Raises:
            Nothing
        """

    @abstractmethod
    def display_progress(self: "PromptBackend", *progress_messages: str) -> None:
        """
        Displays a progress message to the user. Outputs the messages followed
        by a carriage return to seek the cursor to the beginning of the line

        Args:
            *progress_messages (str): Progress messages to display

        Returns:
            None

        Raises:
            Nothing
        """

    @abstractmethod
    def display_table(self: "PromptBackend", table: str) -> None:
        """
        Displays a string containing a rendered table to the user

        Args:
            table (str): The rendered table to display to the user

        Returns:
            None

        Raises:
            Nothing
        """

    @abstractmethod
    def get_command(self: "PromptBackend", initial_input: str | None = None) -> str:
        """
        Prompts the user for command input and returns what they entered

        Args:
            initial_input (str | None): The initial buffer to populate the prompt
                the user with

        Returns:
            str: The command the user entered

        Raises:
            UserExit: If the user requested that the session should be ended
        """

    @abstractmethod
    def hide_cursor(self: "PromptBackend") -> None:
        """
        Hides the terminal cursor from the user

        Args:
            None

        Returns:
            None

        Raises:
            Nothing
        """

    @abstractmethod
    def prompt_for(
        self: "PromptBackend", prompt_series: Iterable[InputModel]
    ) -> List[Any]:
        """
        Prompts the user for a series of inputs according to the provided
        input model.

        Args:
            prompt_series (Iterable[InputModel]): The series of input models
                to prompt the user with

        Returns:
            List[Any]: The responses that the user entered

        Raises:
            Exception: Subclasses may raise exceptions
        """

    @abstractmethod
    def refresh_structure(self: "PromptBackend", structure: SqlStructure) -> None:
        """
        Refreshes the currently cached database structure.

        Args:
            structure (SqlStructure): The database structure to refresh with

        Returns:
            None

        Raises:
            Nothing
        """

    @abstractmethod
    def refresh_style(self: "PromptBackend") -> None: ...

    @abstractmethod
    def show_cursor(self: "PromptBackend") -> None:
        """
        Shows the terminal cursor to the user

        Args:
            None

        Returns:
            None

        Raises:
            Nothing
        """


# pylint: disable=wrong-import-position
from ... import sqlterm
