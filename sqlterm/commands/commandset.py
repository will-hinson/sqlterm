"""
module sqlterm.commands.commandset

Contains all definitions for the CommandSet class which handles
execution when the user types '%set ...' at the command line
"""

from argparse import ArgumentParser
from typing import List

from . import sqltermcommand
from .. import constants
from ..config import TableBackendType

ArgumentParser.exit = sqltermcommand.SqlTermCommand.default_exit  # type: ignore
_command_set_arg_parser: ArgumentParser = ArgumentParser(
    add_help=False,
    exit_on_error=False,
    prog=f"{constants.PREFIX_SQLTERM_COMMAND}set",
    description="A set of commands configuring SQLTerm",
)

_sub_parsers = _command_set_arg_parser.add_subparsers(dest="subcommand")
_sub_parsers.required = True

_command_set_table_backend_parser = _sub_parsers.add_parser(
    "table_backend",
    help="Modifies the current table backend to the provided one",
)
_command_set_table_backend_parser.add_argument("backend_name", type=str)


class CommandSet(sqltermcommand.SqlTermCommand):
    """
    class CommandSet

    Class that handles execution when the user types '%set ...' at the command line
    """

    @property
    def argument_parser(self: "CommandSet") -> ArgumentParser:
        return _command_set_arg_parser

    def execute(self: "CommandSet") -> None:
        match self.args.subcommand:
            case "table_backend":
                self._set_table_backend()
            case _:
                raise NotImplementedError(
                    f"Subcommand '%set {self.args.subcommand}' not implemented"
                )

    @staticmethod
    def get_completions(
        parent, word_before_cursor: str, command_tokens: List[str]
    ) -> List["Suggestion"]:
        return []

    def _set_table_backend(self: "CommandSet") -> None:
        try:
            self.parent.context.config.table_backend = TableBackendType(
                self.args.backend_name
            )
        except Exception as exc:
            self.parent.context.backends.prompt.display_exception(exc)
            return

        self.parent.reset_table_backend()
        self.parent.print_message_sql(
            f"Changed table backend to '{self.args.backend_name}'"
        )
