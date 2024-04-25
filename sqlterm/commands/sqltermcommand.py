from abc import ABCMeta, abstractmethod
from argparse import ArgumentParser, Namespace
import shlex
from typing import Dict, List, Set, Type

from Levenshtein import distance

from .. import constants
from .exceptions import HelpShown, UnknownCommandException

_available_commands: Dict[str, Type["SqlTermCommand"]]


class SqlTermCommand(metaclass=ABCMeta):
    __args: Namespace
    __parent: "sqlterm.SqlTerm"

    def __init__(
        self: "SqlTermCommand", args: List[str], parent: "sqlterm.SqlTerm"
    ) -> None:
        self.__args = self.argument_parser.parse_args(args)
        self.__parent = parent

    @property
    def args(self: "SqlTermCommand") -> Namespace:
        return self.__args

    @property
    @abstractmethod
    def argument_parser(self: "SqlTermCommand") -> ArgumentParser: ...

    @abstractmethod
    def execute(self: "SqlTermCommand") -> None: ...

    @staticmethod
    def default_exit(*args, **kwargs) -> None:
        raise HelpShown()

    @classmethod
    def from_user_input(
        cls: Type["SqlTermCommand"], user_command: str, parent: "sqlterm.SqlTerm"
    ) -> "SqlTermCommand":
        # lex the user's input
        user_args: List[str] = shlex.split(user_command)
        target_command: str = user_args[0].lower()

        # check if the command they entered is known. we do this case-insensitive
        if target_command in _available_commands:
            return _available_commands[target_command](
                args=user_args[1:], parent=parent
            )

        # find the closest command based on edit distance. if it is close, we will
        # display a suggestion to the user
        closest_command: str
        closest_distance: int
        closest_command, closest_distance = min(
            (
                (command_name, distance(target_command, command_name))
                for command_name in _available_commands
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

    @property
    def parent(self: "SqlTermCommand") -> "sqlterm.SqlTerm":
        return self.__parent


# pylint: disable=wrong-import-position
from .. import sqlterm
from .commandalias import CommandAlias
from .commandconnect import CommandConnect
from .commanddisconnect import CommandDisconnect
from .commandexit import CommandExit
from .commandhelp import CommandHelp
from .commandinstall import CommandInstall
from .commandjobs import CommandJobs

_available_commands: Dict[str, Type[SqlTermCommand]] = {
    "alias": CommandAlias,
    "connect": CommandConnect,
    "disconnect": CommandDisconnect,
    "exit": CommandExit,
    "help": CommandHelp,
    "install": CommandInstall,
    "jobs": CommandJobs,
    # these are aliases for the above commands
    "job": CommandJobs,
    "quit": CommandExit,
}

_command_aliases: Set[str] = {"job", "quit"}
