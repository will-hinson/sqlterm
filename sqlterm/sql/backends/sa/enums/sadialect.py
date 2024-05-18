from enum import StrEnum
from typing import Any, Dict


from ..... import constants
from ..dataclasses import ConnectionPromptModel
from ....generic.enums import SqlDialect
from ..prompt_models import MsSqlPromptModel, SqlitePromptModel


class SaDialect(StrEnum):
    MSSQL = "mssql"
    MYSQL = "mysql"
    ORACLE = "oracle"
    POSTGRES = "postgresql"
    SQLITE = "sqlite"


generic_dialect_map: Dict[SaDialect, SqlDialect] = {
    SaDialect.MSSQL: SqlDialect.TSQL,
    SaDialect.MYSQL: SqlDialect.MYSQL,
    SaDialect.ORACLE: SqlDialect.ORACLE,
    SaDialect.POSTGRES: SqlDialect.POSTGRES,
    SaDialect.SQLITE: SqlDialect.SQLITE,
}

dialect_connection_parameters: Dict[SaDialect, Dict[str, Any]] = {
    SaDialect.MSSQL: {
        "App": f"{constants.APPLICATION_NAME} {constants.APPLICATION_VERSION}",
    },
    SaDialect.POSTGRES: {
        "application_name": f"{constants.APPLICATION_NAME} {constants.APPLICATION_VERSION}"
    },
    SaDialect.SQLITE: {"check_same_thread": False},
}


dialect_connection_prompt_models: Dict[SaDialect, ConnectionPromptModel] = {
    SaDialect.MSSQL: MsSqlPromptModel(),
    SaDialect.SQLITE: SqlitePromptModel(),
}
