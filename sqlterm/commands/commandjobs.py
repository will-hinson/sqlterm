from argparse import ArgumentParser
from dataclasses import dataclass
from typing import Dict, List, Tuple

from . import sqltermcommand
from .. import constants
from .dataclasses import JobStatusRecord
from .exceptions import UnknownJobException
from ..sql.exceptions import DisconnectedException
from ..sql.generic import RecordSet
from ..sql.generic.enums import SqlDialect

ArgumentParser.exit = sqltermcommand.SqlTermCommand.default_exit  # type: ignore
_command_jobs_arg_parser: ArgumentParser = ArgumentParser(
    add_help=False,
    exit_on_error=False,
    prog=f"{constants.PREFIX_SQLTERM_COMMAND}jobs",
    description="Allows listing, starting, and stopping of SQL jobs on supported dialects",
)

_sub_parsers = _command_jobs_arg_parser.add_subparsers(dest="subcommand")
_sub_parsers.required = True

_command_jobs_list_parser = _sub_parsers.add_parser(
    "list", help="Lists all SQL jobs including name and current status"
)

_command_jobs_start_parser = _sub_parsers.add_parser(
    "start", help="Starts a SQL job with the provided name"
)
_command_jobs_start_parser.add_argument("job_name")

_command_jobs_status_parser = _sub_parsers.add_parser(
    "status", help="Alias for the '%jobs list' subcommand"
)

_command_jobs_stop_parser = _sub_parsers.add_parser(
    "stop", help="Stops a SQL job with the provided name"
)
_command_jobs_stop_parser.add_argument("job_name", type=str)


@dataclass
class _JobQuerySet:
    get_job_id: str
    list_jobs: str
    start_job_by_id: str
    stop_job_by_id: str


_job_status_column_mapping: Dict[str, str] = {
    "category": "Category",
    "description": "Description",
    "is_enabled": "Enabled?",
    "is_running": "Running?",
    "last_run_datetime": "Last Run Time",
    "last_run_status": "Last Run Status",
    "name": "Job Name",
    "next_run_datetime": "Next Run Time",
    "step_count": "Steps",
}

_queries_for_dialect: Dict[SqlDialect, _JobQuerySet] = {
    SqlDialect.TSQL: _JobQuerySet(
        get_job_id="""
        SELECT
            job_id
        FROM
            msdb.dbo.sysjobs
        WHERE
            [name] = '?';
        """,
        list_jobs="""
        SELECT
            a.[job_id],
            a.[name],
            a.[description],
            category = d.[name],
            f.[step_count],
            is_enabled = CAST(a.[enabled] AS BIT),
            b.[last_run_datetime],
            b.[last_run_status],
            c.[next_run_datetime],
            is_running = CAST(
                IIF(
                    e.[job_id] IS NULL,
                    0,
                    1
                ) AS BIT
            )
        FROM
            msdb.dbo.sysjobs AS a
        LEFT JOIN (
            SELECT
                a.[job_id],
                last_run_datetime = a.[run_datetime],
                last_run_status = COALESCE(
                    b.[human_readable_status],
                    'Unknown'
                )
            FROM (
                SELECT
                    [job_id],
                    run_datetime = msdb.dbo.agent_datetime(
                        [run_date],
                        [run_time]
                    ),
                    [run_status],
                    Rank = ROW_NUMBER() OVER (
                        PARTITION BY
                            [job_id]
                        ORDER BY
                            [instance_id] DESC
                    )
                FROM
                    msdb.dbo.sysjobhistory
            ) AS a
            LEFT JOIN (
                SELECT
                    *
                FROM (
                    VALUES
                        (0, 'Failed'),
                        (1, 'Succeeded'),
                        (2, 'Retry'),
                        (3, 'Canceled'),
                        (4, 'In Progress')
                ) _ (
                    [run_status],
                    [human_readable_status]
                )
            ) AS b ON
                a.[run_status] = b.[run_status]
            WHERE
                [Rank] = 1
        ) AS b ON
            a.[job_id] = b.[job_id]
        LEFT JOIN (
            SELECT
                [job_id],
                next_run_datetime = MIN(
                    msdb.dbo.agent_datetime(
                        [next_run_date],
                        [next_run_time]
                    )
                )
            FROM
                msdb.dbo.sysjobschedules
            GROUP BY
                [job_id]
        ) AS c ON
            a.[job_id] = c.[job_id]
        LEFT JOIN msdb.dbo.syscategories AS d ON
            a.[category_id] = d.[category_id]
        LEFT JOIN (
            SELECT DISTINCT
                [job_id]
            FROM
                msdb.dbo.sysjobactivity
            WHERE
                [stop_execution_date] IS NULL
        ) AS e ON
            a.[job_id] = e.[job_id]
        LEFT JOIN (
            SELECT
                [job_id],
                step_count = COUNT(*)
            FROM
                msdb.dbo.sysjobsteps
            GROUP BY
                [job_id]
        ) AS f ON
            a.[job_id] = f.[job_id];
        """,
        start_job_by_id="""
        EXEC msdb.dbo.sp_start_job
            @job_id = '?';
        """,
        stop_job_by_id="""
        EXEC msdb.dbo.sp_stop_job
            @job_id = '?';
        """,
    )
}


class CommandJobs(sqltermcommand.SqlTermCommand):
    @property
    def argument_parser(self: "CommandJobs") -> ArgumentParser:
        return _command_jobs_arg_parser

    def execute(self: "CommandJobs") -> None:
        # ensure that the target dialect has queries implemented and that the
        # sql backend is currently connected
        if not self.parent.context.backends.sql.connected:
            raise DisconnectedException("No SQL connection is currently established")
        if (
            target_dialect := self.parent.context.backends.prompt.dialect
        ) not in _queries_for_dialect:
            raise NotImplementedError(
                f"%jobs command not implemented for current SQL dialect '{target_dialect}'"
            )

        query_set: _JobQuerySet = _queries_for_dialect[target_dialect]

        # determine which subcommand to perform
        match self.args.subcommand:
            case "list" | "status":
                self._job_list(query_set)
            case "start":
                self._job_start(query_set)
            case "stop":
                self._job_stop(query_set)
            case _:
                raise NotImplementedError(
                    f"Subcommand '%jobs {self.args.subcommand}' not implemented"
                )

    def _fetch_job_id(
        self: "CommandJobs", job_name: str, query_set: _JobQuerySet
    ) -> str:
        results: List[Tuple] = self.parent.context.backends.sql.fetch_results_for(
            self.parent.context.backends.sql.make_query(
                query_set.get_job_id.replace("?", self.args.job_name.replace("'", "''"))
            )
        )

        if len(results) > 0:
            return str(results[0][0])

        raise UnknownJobException(f"A job with name '{job_name}' was not found")

    def _fetch_job_list(
        self: "CommandJobs", query_set: _JobQuerySet
    ) -> List[JobStatusRecord]:
        return [
            JobStatusRecord(*record_tuple)
            for record_tuple in self.parent.context.backends.sql.fetch_results_for(
                self.parent.context.backends.sql.make_query(query_set.list_jobs)
            )
        ]

    def _job_list(self: "CommandJobs", query_set: _JobQuerySet) -> None:
        columns: List[str] = [
            column_name
            for column_name in JobStatusRecord.__annotations__
            if column_name != "job_id"
        ]
        records: List[Tuple] = [
            tuple(
                (value if not isinstance(value, bool) else ("Yes" if value else "No"))
                for value in (getattr(record, column_name) for column_name in columns)
            )
            for record in self._fetch_job_list(query_set)
        ]

        columns = [
            (
                _job_status_column_mapping[column_name]
                if column_name in _job_status_column_mapping
                else column_name
            )
            for column_name in columns
        ]

        print(
            self.parent.context.backends.table.construct_table(
                RecordSet(columns=columns, records=records)
            )
        )

    def _job_start(self: "CommandJobs", query_set: _JobQuerySet) -> None:
        job_id: str = self._fetch_job_id(self.args.job_name, query_set=query_set)
        self.parent.context.backends.prompt.display_message_sql(
            f"Starting job '{self.args.job_name}' (id {job_id})"
        )

        self.parent.context.backends.sql.execute(
            self.parent.context.backends.sql.make_query(
                query_set.start_job_by_id.replace("?", job_id.replace("'", "''"))
            )
        )

    def _job_stop(self: "CommandJobs", query_set: _JobQuerySet) -> None:
        job_id: str = self._fetch_job_id(self.args.job_name, query_set=query_set)
        self.parent.context.backends.prompt.display_message_sql(
            f"Stopping job '{self.args.job_name}' (id {job_id})"
        )

        self.parent.context.backends.sql.execute(
            self.parent.context.backends.sql.make_query(
                query_set.stop_job_by_id.replace("?", job_id.replace("'", "''"))
            )
        )
