from enum import StrEnum

from .sqlprofiler import SqlProfiler


class _MsSqlProfilerQuery(StrEnum):
    NODE_STATUS = """
    SELECT
        c.[node_id],
        c.[physical_operator_name],
        c.[row_count],
        c.[estimate_row_count],
        first_active_time = NULLIF(c.[first_active_time], 0),
        last_active_time = NULLIF(c.[last_active_time], 0)
    FROM (
        SELECT TOP 1
            *
        FROM
            sys.dm_exec_requests
        WHERE
            [session_id] = '?'
    ) AS a
    INNER JOIN sys.dm_exec_query_stats AS b ON
        a.[sql_handle] = b.[sql_handle]
    INNER JOIN sys.dm_exec_query_profiles AS c ON
        a.[sql_handle] = c.[sql_handle];
    """
    QUERY_PLAN_XML = """
    SELECT TOP 1
        [query_plan]
    FROM
        sys.dm_exec_query_plan(
            (
                SELECT TOP 1
                    [plan_handle]
                FROM
                    sys.dm_exec_requests
                WHERE
                    [session_id] = '?'
            )
        );
    """


class MsSqlProfiler(SqlProfiler): ...
