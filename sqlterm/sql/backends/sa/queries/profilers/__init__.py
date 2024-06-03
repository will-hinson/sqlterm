from typing import Dict, Type

from ...enums.sadialect import SaDialect

from .mssqlprofiler import MsSqlProfiler
from .sqlprofiler import SqlProfiler

profiler_for_dialect: Dict[SaDialect, Type[SqlProfiler]] = {
    SaDialect.MSSQL: MsSqlProfiler,
}
