"""
module sqlterm.commands.sqltermcommand

Contains the definition of the SqlTermCommand metaclass which is the base
class of all builtin command classes in sqlterm. Also contains the available_commands
dict which maps all command names to their respective classes.
"""

from abc import ABCMeta, abstractmethod
from argparse import ArgumentParser, Namespace
import shlex
from typing import Dict, List, Set, Type

from Levenshtein import distance

from .. import constants
from .exceptions import HelpShown, UnknownCommandException

available_commands: Dict[str, Type["SqlTermCommand"]]


class SqlTermCommand(metaclass=ABCMeta):
    """
    class SqlTermCommand

    A metaclass which is the base class of all builtin command classes in sqlterm
    """

    __args: Namespace
    __parent: "sqlterm.SqlTerm"

    def __init__(
        self: "SqlTermCommand", args: List[str], parent: "sqlterm.SqlTerm"
    ) -> None:
        self.__args = self.argument_parser.parse_args(args)
        self.__parent = parent

    @property
    def args(self: "SqlTermCommand") -> Namespace:
        """
        Property that returns all of the argument values that were provided when
        the user invoked this command.

        Args:
            None

        Returns:
            Namespace: The argument values that were provided when the user invoked
                this command

        Raises:
            Nothing
        """

        return self.__args

    @property
    @abstractmethod
    def argument_parser(self: "SqlTermCommand") -> ArgumentParser:
        """
        Returns the argument parser for this specific SqlTermCommand subclass.

        Args:
            None

        Returns:
            ArgumentParser: The ArgumentParser that can be used to parse arguments
                for this sqlterm command

        Raises:
            Nothing
        """

    @abstractmethod
    def execute(self: "SqlTermCommand") -> None:
        """
        Begins execution of the command implemented the SqlTermCommand subclass
        using the arguments that were passed during instantiation.

        Args:
            None

        Returns:
            Nothing

        Raises:
            SqlTermException: Any exceptions thrown either directly by the command
            or any backend methods that it may invoke
        """

    @staticmethod
    def default_exit(*args, **kwargs) -> None:
        """
        A static method intended to
        """

        raise HelpShown()

    @classmethod
    def from_user_input(
        cls: Type["SqlTermCommand"], user_command: str, parent: "sqlterm.SqlTerm"
    ) -> "SqlTermCommand":
        """
        Parse the command input provided by the user and constructs a SqlTermCommand
        subclass instance around it. This instance is ready to be run with execute()

        Args:
            user_command (str): The command that the user entered. Any sigils should
                be removed
            parent (SqlTerm): The sqlterm session to register as the command's parent

        Returns:
            SqlTermCommand: A SqlTermCommand instance based on the user's input

        Raises:
            UnknownCommandException: If the command the user entered wasn't known
        """

        # lex the user's input
        user_args: List[str] = shlex.split(user_command)
        target_command: str = user_args[0].lower()

        # check if the command they entered is known. we do this case-insensitive
        if target_command in available_commands:
            return available_commands[target_command](args=user_args[1:], parent=parent)

        # find the closest command based on edit distance. if it is close, we will
        # display a suggestion to the user
        closest_command: str
        closest_distance: int
        closest_command, closest_distance = min(
            (
                (command_name, distance(target_command, command_name))
                for command_name in available_commands
            ),
            key=lambda distance_tuple: distance_tuple[-1],
        )

        raise UnknownCommandException(
            f"Unknown command '{user_args[0]}'"
            + (
                f" (did you mean '{closest_command}'?)"
                if closest_distance <= constants.COMMAND_SUGGESTION_MAX_DISTANCE
                else ""
            )
        )

    @staticmethod
    @abstractmethod
    def get_completions(
        parent, word_before_cursor: str, command_tokens: List[str]
    ) -> List["Suggestion"]: ...

    @property
    def parent(self: "SqlTermCommand") -> "sqlterm.SqlTerm":
        """
        Returns the parent SqlTerm instance where this SqlTermCommand was invoked.

        Args:
            Nothing

        Returns:
            SqlTerm: The parent SqlTerm instance where this SqlTermCommand was invoked

        Raises:
            Nothing
        """

        return self.__parent


# pylint: disable=wrong-import-position
from .. import sqlterm
from .commandalias import CommandAlias
from .commandbrowse import CommandBrowse
from .commandconnect import CommandConnect
from .commanddisconnect import CommandDisconnect
from .commandedit import CommandEdit
from .commandexit import CommandExit
from .commandhelp import CommandHelp
from .commandinstall import CommandInstall
from .commandjobs import CommandJobs

available_commands: Dict[str, Type[SqlTermCommand]] = {
    "alias": CommandAlias,
    "connect": CommandConnect,
    "browse": CommandBrowse,
    "disconnect": CommandDisconnect,
    "edit": CommandEdit,
    "exit": CommandExit,
    "help": CommandHelp,
    "install": CommandInstall,
    "jobs": CommandJobs,
    # these are aliases for the above commands
    "job": CommandJobs,
    "quit": CommandExit,
}

command_aliases: Set[str] = {"job", "quit"}
