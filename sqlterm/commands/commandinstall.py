from argparse import ArgumentParser
import subprocess
import sys
from typing import List

from . import sqltermcommand
from .. import constants

ArgumentParser.exit = sqltermcommand.SqlTermCommand.default_exit  # type: ignore
_command_insert_arg_parser: ArgumentParser = ArgumentParser(
    add_help=False,
    exit_on_error=False,
    prog=f"{constants.PREFIX_SQLTERM_COMMAND}insert",
)
_command_insert_arg_parser.add_argument("driver_string", type=str)


class CommandInstall(sqltermcommand.SqlTermCommand):
    @property
    def argument_parser(self: "CommandInstall") -> ArgumentParser:
        return _command_insert_arg_parser

    def execute(self: "CommandInstall") -> None:
        required_packages: List[str] = (
            self.parent.context.backends.sql.required_packages_for_dialect(
                self.args.driver_string
            )
        )
        print(
            f"Detected {len(required_packages)} required package"
            f"{'s' if len(required_packages) != 1 else ''} for dialect '{self.args.driver_string}'"
        )

        for package in required_packages:
            print(f"Installing target {package}")
            self._install_package(target_package=package)

    def _install_package(self: "CommandInstall", target_package: str) -> None:
        subprocess.check_call([sys.executable, "-m", "pip", "install", target_package])
