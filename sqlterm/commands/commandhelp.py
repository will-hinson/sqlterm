"""
module sqlterm.commands.commandhelp

Contains all definitions for the CommandHelp class which handles
execution when the user types '%help ...' at the command line
"""

from argparse import ArgumentParser
import shutil
from typing import List

from .. import constants
from . import sqltermcommand
from ..prompt.dataclasses import Suggestion

ArgumentParser.exit = sqltermcommand.SqlTermCommand.default_exit  # type: ignore
_command_help_arg_parser: ArgumentParser = ArgumentParser(
    add_help=False,
    exit_on_error=False,
    prog=f"{constants.PREFIX_SQLTERM_COMMAND}help",
)
_command_help_arg_parser.add_argument("command_name", type=str, nargs="?")


class CommandHelp(sqltermcommand.SqlTermCommand):
    """
    class CommandHelp

    Class that handles execution when the user types '%help ...' at the command line
    """

    @property
    def argument_parser(self: "CommandHelp") -> ArgumentParser:
        return _command_help_arg_parser

    def _display_command_help(
        self: "CommandHelp", command_arg_parser: ArgumentParser
    ) -> None:
        help_lines: List[str] = command_arg_parser.format_help().splitlines()

        self.parent.context.backends.prompt.display_message_sql(
            help_lines[0][6:].strip()
            if help_lines[0].lower().startswith("usage:")
            else help_lines[0]
        )

        for help_line in help_lines[1:]:
            print(help_line)

    def execute(self: "CommandHelp") -> None:
        if self.args.command_name is None:
            for command_name in sorted(
                command_name
                for command_name in sqltermcommand.available_commands
                # exclude known command aliases
                if command_name not in sqltermcommand.command_aliases
            ):
                self._show_help_for_command(command_name)
                self.parent.context.backends.prompt.display_info("")
                self.parent.context.backends.prompt.display_info(
                    "-" * shutil.get_terminal_size().columns
                )
        else:
            self._show_help_for_command(self.args.command_name)

    @staticmethod
    def get_completions(
        parent, word_before_cursor: str, command_tokens: List[str]
    ) -> List[Suggestion]:
        return []

    def _show_help_for_command(self: "CommandHelp", command_name: str) -> None:
        # pylint: disable=protected-access
        if command_name not in sqltermcommand.available_commands:
            raise NotImplementedError(
                f"Unable to show help for command '{command_name}'"
            )

        # get the arg parser from the command using the argument_parser property.
        # technically, the argument_parser property needs to be bound to an
        # instance, but here we call it without being bound
        command_arg_parser: ArgumentParser = sqltermcommand.available_commands[
            command_name
        ].argument_parser.fget(
            None
        )  # type: ignore

        self._display_command_help(command_arg_parser)
