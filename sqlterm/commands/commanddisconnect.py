from argparse import ArgumentParser

from . import sqltermcommand
from .. import constants

ArgumentParser.exit = sqltermcommand.SqlTermCommand.default_exit  # type: ignore
_command_disconnect_arg_parser: ArgumentParser = ArgumentParser(
    add_help=False,
    exit_on_error=False,
    prog=f"{constants.PREFIX_SQLTERM_COMMAND}disconnect",
)


class CommandDisconnect(sqltermcommand.SqlTermCommand):
    @property
    def argument_parser(self: "CommandDisconnect") -> ArgumentParser:
        return _command_disconnect_arg_parser

    def execute(self: "CommandDisconnect") -> None:
        self.parent.context.backends.sql.disconnect()
