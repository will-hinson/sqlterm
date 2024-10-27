"""
module sqlterm.config.sqltermconfig

Contains the definition of the SqlTermConfig class, a dataclass that represents
a set of sqlterm configurations
"""

from dataclasses import dataclass
import json
import os
from typing import Any, Callable, Dict, List, Tuple, NoReturn, Type

from dataclasses_json import dataclass_json
import platformdirs

from .. import constants
from .alias import Alias
from .tablebackendtype import TableBackendType


_config_upgrade_order: List[
    Tuple[str, Callable[["SqlTermConfig", str], "SqlTermConfig"]]
]


@dataclass_json
@dataclass
class SqlTermConfig:
    """
    class SqlTermConfig

    Dataclass that represents a set of sqlterm configurations
    """

    version: str
    aliases: Dict[str, Alias]
    color_scheme: str
    autoformat: bool
    table_backend: TableBackendType

    @staticmethod
    def cannot_upgrade(from_config: "SqlTermConfig", to_version: str) -> NoReturn:
        """
        Constructs and throws an appropriate exception for when a configuration cannot
        be upgraded to a specific version

        Args:
            from_config (SqlTermConfig): The configuration instance that was
                being upgraded
            to_version (str): The version that the configuration was being upgraded to

        Returns:
            Nothing

        Raises:
            NotImplementedError: An appropriate error based on the person the config was
                being upgraded to
        """

        raise NotImplementedError(
            f"Cannot upgrade config from version {from_config.version} to version {to_version}"
        )

    @staticmethod
    def default_path() -> str:
        """
        Returns the default path that the current user's configuration should be read from

        Args:
            None

        Returns:
            str: The path where the current user's configuration file should be

        Raises:
            Nothing
        """

        return os.path.join(
            platformdirs.user_data_dir(
                appname=constants.APPLICATION_NAME,
                version=constants.APPLICATION_VERSION,
            ),
            "config.json",
        )

    @staticmethod
    def _ensure_directory(dir_path: str) -> None:
        if not os.path.isdir(dir_path):
            os.makedirs(dir_path)

    @staticmethod
    def _ensure_file(file_path: str) -> None:
        # first, ensure the directory exists
        SqlTermConfig._ensure_directory(os.path.dirname(file_path))

        # then, create the file if needed
        if not os.path.isfile(file_path):
            SqlTermConfig.make_default().to_file(file_path)

    @classmethod
    def from_dict(
        cls: Type["SqlTermConfig"], json_data: Dict[str, Any]
    ) -> "SqlTermConfig":
        """
        Constructs a SqlTermConfig instance from the provided json dict

        Args:
            json_data (Dict[str, Any]): The json data from which to construct the
                SqlTermConfig

        Returns:
            SqlTermConfig: A SqlTermConfig instance containing the data from the
                provided dict

        Raises:
            Exception: If the provided dict does not match the expected layout
                of a SqlTermConfig instance
        """

        return SqlTermConfig(**json_data)

    @classmethod
    def from_file(cls: Type["SqlTermConfig"], path: str) -> "SqlTermConfig | None":
        """
        Constructs a SqlTermConfig instance from the provided JSON file

        Args:
            path (str): The file to read JSON config data from

        Returns:
            SqlTermConfig: A SqlTermConfig instance containing the data from the
                provided file

        Raises:
            Exception: If the provided file contents do not match the expected
                layout of a SqlTermConfig instance
        """

        # check if the config file exists and create it if not
        SqlTermConfig._ensure_file(path)

        # pylint: disable=broad-exception-caught
        try:
            with open(path, "r", encoding="utf-8") as config_file:
                return SqlTermConfig.from_dict(json.loads(config_file.read()))
        except Exception as exc:
            print(f"Unable to read config from target path '{path}': {exc}")
            return None

    @staticmethod
    def make_default() -> "SqlTermConfig":
        """
        Constructs a SqlTermConfig instance containing the default configuration

        Args:
            None

        Returns:
            SqlTermConfig: Instance containing default settings

        Raises:
            Nothing
        """

        return SqlTermConfig(
            version=constants.CONFIG_VERSION,
            aliases={},
            color_scheme="tokyo-night-dark",
            autoformat=False,
            table_backend=TableBackendType.SQLTERM_TABLES,
        )

    def to_file(self: "SqlTermConfig", output_path: str) -> None:
        """
        Writes this SqlTermConfig instance to the file with the specified path as
        JSON data.

        Args:
            output_path (str): The path of the file to write the config to

        Returns:
            Nothing

        Raises:
            Exception: If the file was unable to be written to
        """

        with open(output_path, "w", encoding="utf-8") as output_file:
            # pylint: disable=no-member
            print(self.to_json(indent=2), file=output_file)


_config_upgrade_order = [("0.1", SqlTermConfig.cannot_upgrade)]
