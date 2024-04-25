from typing import Dict, Type

from .defaultmanager import DefaultManager
from .mssqlmanager import MsSqlManager
from .postgresmanager import PostgresManager
from .querymanager import QueryManager
from .sqlitemanager import SqliteManager

from ...enums import SaDialect

query_manager_for_dialect: Dict[SaDialect, Type[QueryManager]] = {
    SaDialect.MSSQL: MsSqlManager,
    SaDialect.POSTGRES: PostgresManager,
    SaDialect.SQLITE: SqliteManager,
}
