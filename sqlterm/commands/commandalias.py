"""
module sqlterm.commands.commandalias

Contains all definitions for the CommandAlias class which handles
execution when the user types '%alias ...' at the command line
"""

from argparse import ArgumentParser
from typing import List

from . import sqltermcommand
from .. import constants
from .exceptions import AliasExistsException, NoAliasExistsException

ArgumentParser.exit = sqltermcommand.SqlTermCommand.default_exit  # type: ignore
_command_alias_arg_parser: ArgumentParser = ArgumentParser(
    add_help=False,
    exit_on_error=False,
    prog=f"{constants.PREFIX_SQLTERM_COMMAND}alias",
    description="A set of commands for working with database connection aliases",
)

_sub_parsers = _command_alias_arg_parser.add_subparsers(dest="subcommand")
_sub_parsers.required = True

_command_alias_create_parser = _sub_parsers.add_parser(
    "create",
    help="Creates an alias with the specified name for the provided connection string",
)
_command_alias_create_parser.add_argument("alias_name", type=str)
_command_alias_create_parser.add_argument(
    "connection_string", type=str, nargs="?", default=None
)

_command_alias_list_parser = _sub_parsers.add_parser(
    "list", help="Displays a list of all currently registered aliases"
)

_command_alias_remove_parser = _sub_parsers.add_parser(
    "remove", help="Removes the alias with the provided name"
)
_command_alias_remove_parser.add_argument("alias_name", type=str)


class CommandAlias(sqltermcommand.SqlTermCommand):
    """
    class CommandAlias

    Class that handles execution when the user types '%alias ...' at the command line
    """

    @property
    def argument_parser(self: "CommandAlias") -> ArgumentParser:
        return _command_alias_arg_parser

    def _alias_create(self: "CommandAlias") -> None:
        alias_connection_string: str
        should_test: bool
        if self.args.connection_string is not None:
            alias_connection_string = self.args.connection_string
            should_test = True
        else:
            alias_connection_string = self.parent.context.backends.sql.connection_string
            should_test = False

        if self.args.alias_name in self.parent.context.config.aliases:
            raise AliasExistsException(
                f"An alias with the name '{self.args.alias_name}' already exists"
            )

        self.parent.create_alias(
            self.args.alias_name,
            self.parent.context.backends.sql.resolve_connection_string(
                alias_connection_string, test_connection=should_test
            ),
        )

    def _alias_list(self: "CommandAlias") -> None:
        for alias_name in sorted(self.parent.context.config.aliases):
            self.parent.print_message_sql(alias_name)

    def _alias_remove(self: "CommandAlias") -> None:
        if self.args.alias_name not in self.parent.context.config.aliases:
            raise NoAliasExistsException(
                f"No known alias named '{self.args.alias_name}' exists"
            )

        self.parent.remove_alias(self.args.alias_name)

    def execute(self: "CommandAlias") -> None:
        match self.args.subcommand:
            case "create":
                self._alias_create()
            case "list":
                self._alias_list()
            case "remove":
                self._alias_remove()
            case _:
                raise NotImplementedError(
                    f"Subcommand '%alias {self.args.subcommand}' not implemented"
                )

    @staticmethod
    def get_completions(
        word_before_cursor: str, command_tokens: List[str]
    ) -> List["Suggestion"]:
        return []
