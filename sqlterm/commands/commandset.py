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
from .exceptions import InvalidArgumentException, NoAliasExistsException
from ..sql.exceptions import DisconnectedException

ArgumentParser.exit = sqltermcommand.SqlTermCommand.default_exit  # type: ignore
_command_set_arg_parser: ArgumentParser = ArgumentParser(
    add_help=False,
    exit_on_error=False,
    prog=f"{constants.PREFIX_SQLTERM_COMMAND}set",
    description="A set of commands configuring SQLTerm",
)

_sub_parsers = _command_set_arg_parser.add_subparsers(dest="subcommand")
_sub_parsers.required = True

_command_set_autoformat = _sub_parsers.add_parser(
    "autoformat",
    help="Modifies the setting for autoformatting SQL input",
)
_command_set_autoformat.add_argument("on_or_off", type=str, choices=["off", "on"])

_command_set_prompt_color_parser = _sub_parsers.add_parser(
    "prompt_color",
    help="Modifies the prompt color for the selected alias",
)
_command_set_prompt_color_parser.add_argument("color", type=str)

_command_set_table_backend_parser = _sub_parsers.add_parser(
    "table_backend",
    help="Modifies the current table backend to the provided one",
)
_command_set_table_backend_parser.add_argument(
    "backend_name",
    type=str,
    choices=TableBackendType,
)


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
            case "autoformat":
                self._set_autoformat()
            case "prompt_color":
                self._set_prompt_color()
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
        # pylint: disable=import-outside-toplevel
        from ..prompt.dataclasses import Suggestion

        # check if the user is typing a subcommand
        if len(command_tokens) == 1 or word_before_cursor == command_tokens[1]:
            return [
                Suggestion(
                    setting_name, position=-len(word_before_cursor), suffix="setting"
                )
                for setting_name in _sub_parsers.choices.keys()
                if (
                    word_before_cursor in setting_name
                    or setting_name in word_before_cursor
                )
            ]
        if len(command_tokens) == 2 or word_before_cursor == command_tokens[2]:
            match command_tokens[1]:
                case "autoformat":
                    return [
                        Suggestion(
                            setting_value,
                            position=-len(word_before_cursor),
                            suffix="setting",
                        )
                        for setting_value in ["on", "off"]
                        if word_before_cursor in setting_value
                        or setting_value in word_before_cursor
                    ]
                case "table_backend":
                    return [
                        Suggestion(
                            backend_name,
                            position=-len(word_before_cursor),
                            suffix="backend",
                        )
                        for backend_name in TableBackendType
                        if word_before_cursor in backend_name
                        or backend_name in word_before_cursor
                    ]

        return []

    def _set_autoformat(self: "CommandSet") -> None:
        autoformat_setting: bool
        match self.args.on_or_off:
            case "on":
                autoformat_setting = True
            case "off":
                autoformat_setting = False
            case _:
                raise InvalidArgumentException(
                    f"Invalid setting '{self.args.on_or_off}' for autoformat"
                )

        self.parent.set_autoformat(autoformat_setting)

    def _set_prompt_color(self: "CommandSet") -> None:
        if not self.parent.context.backends.sql.connected:
            raise DisconnectedException(
                "An aliased connection must be established first"
            )
        if self.parent.context.backends.sql.alias is None:
            raise NoAliasExistsException(
                "The current connection does not have an alias"
            )

        # check that the color is a valid color for the prompt backend. if the color is 'default',
        # skip this check
        if (
            self.args.color != "default"
            and not self.parent.context.backends.prompt.is_valid_color(self.args.color)
        ):
            raise InvalidArgumentException("Invalid color argument for prompt_color")
        if self.args.color == "default":
            self.args.color = None

        self.parent.set_alias_prompt_color(
            self.parent.context.backends.sql.alias, self.args.color
        )

    def _set_table_backend(self: "CommandSet") -> None:
        try:
            self.parent.context.config.table_backend = TableBackendType(
                self.args.backend_name
            )
        # pylint: disable=broad-exception-caught
        except Exception as exc:
            self.parent.context.backends.prompt.display_exception(exc)
            return

        self.parent.reset_table_backend()
        self.parent.print_message_sql(
            f"Changed table backend to '{self.args.backend_name}'"
        )
