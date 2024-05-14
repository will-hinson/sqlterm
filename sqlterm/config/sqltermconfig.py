from dataclasses import dataclass
import json
import os
from typing import Any, Callable, Dict, List, Tuple, Type

from dataclasses_json import dataclass_json
import platformdirs

from .. import constants
from .alias import Alias


_config_upgrade_order: List[
    Tuple[str, Callable[["SqlTermConfig", str], "SqlTermConfig"]]
]


@dataclass_json
@dataclass
class SqlTermConfig:
    version: str
    aliases: Dict[str, Alias]
    color_scheme: str

    @staticmethod
    def cannot_upgrade(
        from_config: "SqlTermConfig", to_version: str
    ) -> "SqlTermConfig":
        raise NotImplementedError(
            f"Cannot upgrade config from version {from_config.version} to version {to_version}"
        )

    @staticmethod
    def default_path() -> str:
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
        return SqlTermConfig(**json_data)

    @classmethod
    def from_file(cls: Type["SqlTermConfig"], path: str) -> "SqlTermConfig | None":
        # check if the config file exists and create it if not
        SqlTermConfig._ensure_file(path)

        # pylint: disable=broad-exception-caught
        try:
            with open(path, "r", encoding="utf-8") as config_file:
                return SqlTermConfig.from_dict(json.loads(config_file.read()))
        except Exception as exc:
            print(f"Unable to read config from target path '{path}': {exc}")

    @staticmethod
    def make_default() -> "SqlTermConfig":
        return SqlTermConfig(
            version=constants.CONFIG_VERSION, aliases={}, color_scheme="dracula"
        )

    def to_file(self: "SqlTermConfig", output_path: str) -> None:
        with open(output_path, "w", encoding="utf-8") as output_file:
            print(self.to_json(indent=2), file=output_file)


_config_upgrade_order = [("0.1", SqlTermConfig.cannot_upgrade)]
