"""
module sqlterm.commands.commandconnect

Contains all definitions for the CommandConnect class which handles
execution when the user types '%connect ...' at the command line
"""

from argparse import ArgumentParser
from typing import List

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
    """
    class CommandConnect

    Class that handles execution when the user types '%connect ...' at the command line
    """

    @property
    def argument_parser(self: "CommandConnect") -> ArgumentParser:
        return _command_connect_arg_parser

    def execute(self: "CommandConnect") -> None:
        # connect to the provided server
        try:
            self.parent.context.backends.sql.connect(self.args.connection_string)
            if (alias_name := self.parent.context.backends.sql.alias) is not None:
                self.parent.context.backends.prompt.set_prompt_color(
                    self.parent.context.config.aliases[alias_name].prompt_color
                )
        except MissingModuleException:
            print(
                "Hint: Try running the 'install' command for the driver/dialect in "
                "the provided connection string"
            )
            raise
        except (KeyboardInterrupt, EOFError):
            # the user interrupted the action
            ...

    @staticmethod
    def get_completions(
        parent, word_before_cursor: str, command_tokens: List[str]
    ) -> List["Suggestion"]:
        from ..prompt.dataclasses import Suggestion

        word_before_cursor = word_before_cursor.lower()

        if len(command_tokens) < 3:
            return [
                Suggestion(
                    alias_name, position=-len(word_before_cursor), suffix="alias"
                )
                for alias_name in parent.context.config.aliases
                if len(word_before_cursor) == 0
                or alias_name.lower().startswith(word_before_cursor)
                or word_before_cursor in alias_name.lower()
            ]

        return []
