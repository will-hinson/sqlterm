from argparse import ArgumentParser
import sys

from . import sqltermcommand
from .. import constants

ArgumentParser.exit = sqltermcommand.SqlTermCommand.default_exit  # type: ignore
_command_exit_arg_parser: ArgumentParser = ArgumentParser(
    add_help=False,
    exit_on_error=False,
    prog=f"{constants.PREFIX_SQLTERM_COMMAND}exit",
)


class CommandExit(sqltermcommand.SqlTermCommand):
    @property
    def argument_parser(self: "CommandExit") -> ArgumentParser:
        return _command_exit_arg_parser

    def execute(self: "CommandExit") -> None:
        sys.exit(0)
