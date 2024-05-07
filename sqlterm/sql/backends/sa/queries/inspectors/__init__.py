from typing import Dict, Type

from .defaultinspector import DefaultInspector
from .mssqlinspector import MsSqlInspector
from .mysqlinspector import MySqlInspector
from .postgresinspector import PostgresInspector
from .sqlinspector import SqlInspector
from .sqliteinspector import SqliteInspector

from ...enums import SaDialect

sql_inspector_for_dialect: Dict[SaDialect, Type[SqlInspector]] = {
    SaDialect.MSSQL: MsSqlInspector,
    SaDialect.MYSQL: MySqlInspector,
    SaDialect.POSTGRES: PostgresInspector,
    SaDialect.SQLITE: SqliteInspector,
}
