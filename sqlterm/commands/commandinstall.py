"""
module sqlterm.commands.commandinstall

Contains all definitions for the CommandInstall class which handles
execution when the user types '%install ...' at the command line
"""

from argparse import ArgumentParser
import subprocess
import sys
from typing import List

from . import sqltermcommand
from .. import constants
from ..prompt.dataclasses import Suggestion

ArgumentParser.exit = sqltermcommand.SqlTermCommand.default_exit  # type: ignore
_command_install_arg_parser: ArgumentParser = ArgumentParser(
    add_help=False,
    exit_on_error=False,
    prog=f"{constants.PREFIX_SQLTERM_COMMAND}install",
    description=(
        "Installs any packages required for connecting to databases or servers of "
        "the provided dialect if the dialect is known."
    ),
)
_command_install_arg_parser.add_argument(
    "dialect_string",
    type=str,
    help="The name of the dialect/driver combination (i.e., mssql+pyodbc)",
)


class CommandInstall(sqltermcommand.SqlTermCommand):
    """
    class CommandInstall

    Class that handles execution when the user types '%install ...' at the command line
    """

    @property
    def argument_parser(self: "CommandInstall") -> ArgumentParser:
        return _command_install_arg_parser

    def execute(self: "CommandInstall") -> None:
        required_packages: List[str] = (
            self.parent.context.backends.sql.required_packages_for_dialect(
                self.args.dialect_string
            )
        )
        print(
            f"Detected {len(required_packages)} required package"
            f"{'s' if len(required_packages) != 1 else ''} for dialect '{self.args.dialect_string}'"
        )

        for package in required_packages:
            print(f"Installing target {package}")
            self._install_package(target_package=package)

    @staticmethod
    def get_completions(
        parent, word_before_cursor: str, command_tokens: List[str]
    ) -> List[Suggestion]:
        if len(command_tokens) == 1 or word_before_cursor == command_tokens[1]:
            return [
                Suggestion(
                    dialect_name, position=-len(word_before_cursor), suffix="dialect"
                )
                for dialect_name in parent.context.backends.sql.dialect_to_package_map
                if word_before_cursor in dialect_name
                or dialect_name in word_before_cursor
            ]

        return []

    def _install_package(self: "CommandInstall", target_package: str) -> None:
        subprocess.check_call([sys.executable, "-m", "pip", "install", target_package])
