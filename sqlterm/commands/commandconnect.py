from argparse import ArgumentParser

from . import sqltermcommand
from .. import constants
from ..sql.exceptions import MissingModuleException

ArgumentParser.exit = sqltermcommand.SqlTermCommand.default_exit  # type: ignore
_command_connect_arg_parser: ArgumentParser = ArgumentParser(
    add_help=False,
    exit_on_error=False,
    prog=f"{constants.PREFIX_SQLTERM_COMMAND}connect",
    description=(
        "Connects to the database referenced in the provided connection string. "
        "The connection string may be an alias, a SQL dialect/driver name, or a full "
        "SQLAlchemy connection string"
    ),
)
_command_connect_arg_parser.add_argument(
    "connection_string",
    type=str,
    help="A reference to the database to connect to",
)


class CommandConnect(sqltermcommand.SqlTermCommand):
    @property
    def argument_parser(self: "CommandConnect") -> ArgumentParser:
        return _command_connect_arg_parser

    def execute(self: "CommandConnect") -> None:
        # connect to the provided server
        try:
            self.parent.context.backends.sql.connect(self.args.connection_string)
        except MissingModuleException:
            print(
                "Hint: Try running the 'install' command for the driver/dialect in "
                "the provided connection string"
            )
            raise
        except (KeyboardInterrupt, EOFError):
            # the user interrupted the action
            ...
