from typing import Dict, Type

from .defaultinspector import DefaultInspector
from .mssqlinspector import MsSqlInspector
from .mysqlinspector import MySqlInspector
from .oracleinspector import OracleInspector
from .postgresinspector import PostgresInspector
from .redshiftinspector import RedshiftInspector
from .sqlinspector import SqlInspector
from .sqliteinspector import SqliteInspector

from ...enums import SaDialect

sql_inspector_for_dialect: Dict[SaDialect, Type[SqlInspector]] = {
    SaDialect.MSSQL: MsSqlInspector,
    SaDialect.MYSQL: MySqlInspector,
    SaDialect.ORACLE: OracleInspector,
    SaDialect.POSTGRES: PostgresInspector,
    SaDialect.REDSHIFT: RedshiftInspector,
    SaDialect.SQLITE: SqliteInspector,
}
