"""
module sqlterm.commands.commandbrowse

Contains all definitions for the CommandBrowse class which handles
execution when the user types '%browse ...' at the command line
"""

from argparse import ArgumentParser
from typing import List

from . import sqltermcommand
from .. import constants

ArgumentParser.exit = sqltermcommand.SqlTermCommand.default_exit  # type: ignore
_command_browse_arg_parser: ArgumentParser = ArgumentParser(
    add_help=False,
    exit_on_error=False,
    prog=f"{constants.PREFIX_SQLTERM_COMMAND}browse",
    description="Displays a database object browser for supported dialects",
)


class CommandBrowse(sqltermcommand.SqlTermCommand):
    """
    class CommandBrowse

    Class that handles execution when the user types '%browse ...' at the command line
    """

    @property
    def argument_parser(self: "CommandBrowse") -> ArgumentParser:
        return _command_browse_arg_parser

    def execute(self: "CommandBrowse") -> None:
        self.parent.context.backends.prompt.display_object_browser(show_loading=True)

    @staticmethod
    def get_completions(
        word_before_cursor: str, command_tokens: List[str]
    ) -> List["Suggestion"]:
        return []
