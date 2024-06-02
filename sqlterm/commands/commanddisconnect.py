"""
module sqlterm.commands.commanddisconnect

Contains all definitions for the CommandDisconnect class which handles
execution when the user types '%disconnect ...' at the command line
"""

from argparse import ArgumentParser
from typing import List

from . import sqltermcommand
from .. import constants

ArgumentParser.exit = sqltermcommand.SqlTermCommand.default_exit  # type: ignore
_command_disconnect_arg_parser: ArgumentParser = ArgumentParser(
    add_help=False,
    exit_on_error=False,
    prog=f"{constants.PREFIX_SQLTERM_COMMAND}disconnect",
    description="Terminates any currently active SQL connection",
)


class CommandDisconnect(sqltermcommand.SqlTermCommand):
    """
    class CommandDisconnect

    Class that handles execution when the user types '%disconnect ...' at the command line
    """

    @property
    def argument_parser(self: "CommandDisconnect") -> ArgumentParser:
        return _command_disconnect_arg_parser

    def execute(self: "CommandDisconnect") -> None:
        self.parent.context.backends.sql.disconnect()

    @staticmethod
    def get_completions(
        word_before_cursor: str, command_tokens: List[str]
    ) -> List["Suggestion"]:
        return []
