"""
module sqlterm.commands.commandexit

Contains all definitions for the CommandExit class which handles
execution when the user types '%exit ...' at the command line
"""

from argparse import ArgumentParser
import sys

from . import sqltermcommand
from .. import constants

ArgumentParser.exit = sqltermcommand.SqlTermCommand.default_exit  # type: ignore
_command_exit_arg_parser: ArgumentParser = ArgumentParser(
    add_help=False,
    exit_on_error=False,
    prog=f"{constants.PREFIX_SQLTERM_COMMAND}exit",
    description="Exits the current sqlterm session terminating any active SQL connection",
)


class CommandExit(sqltermcommand.SqlTermCommand):
    """
    class CommandExit

    Class that handles execution when the user types '%exit ...' at the command line
    """

    @property
    def argument_parser(self: "CommandExit") -> ArgumentParser:
        return _command_exit_arg_parser

    def execute(self: "CommandExit") -> None:
        sys.exit(0)
