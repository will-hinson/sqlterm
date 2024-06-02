"""
module sqlterm.commands.commandjobs

Contains all definitions for the CommandJobs class which handles
execution when the user types '%jobs ...' at the command line
"""

from argparse import ArgumentParser
from dataclasses import dataclass, astuple
from typing import Dict, List, Tuple

from . import sqltermcommand
from .. import constants
from .dataclasses import JobLastRunDetails, JobStatusRecord, JobStep
from .exceptions import UnknownJobException
from ..prompt.dataclasses import Suggestion
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

_command_jobs_detail_parser = _sub_parsers.add_parser(
    "detail", help="Gets details regarding a specific job include stats on recent runs"
)
_command_jobs_detail_parser.add_argument("job_name")

_command_jobs_list_parser = _sub_parsers.add_parser(
    "list", help="Lists all SQL jobs including name and current status"
)

_command_jobs_start_parser = _sub_parsers.add_parser(
    "start", help="Starts a SQL job with the provided name"
)
_command_jobs_start_parser.add_argument("job_name")

_command_jobs_status_parser = _sub_parsers.add_parser(
    "status", help="Alias for the '%%jobs list' subcommand"
)

_command_jobs_stop_parser = _sub_parsers.add_parser(
    "stop", help="Stops a SQL job with the provided name"
)
_command_jobs_stop_parser.add_argument("job_name", type=str)


@dataclass
class _JobQuerySet:
    get_job_description: str
    get_job_id: str
    get_job_last_run: str
    get_job_steps: str
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
        get_job_description="""
        SELECT
            description
        FROM
            msdb.dbo.sysjobs
        WHERE
            [job_id] = '?';
        """,
        get_job_id="""
        SELECT
            job_id
        FROM
            msdb.dbo.sysjobs
        WHERE
            [name] = '?';
        """,
        get_job_last_run="""
        WITH cteRunSourceIDs AS (
            SELECT
                *
            FROM (
                VALUES
                    (1, 'Scheduler'),
                    (2, 'Alterer'),
                    (3, 'Boot'),
                    (4, 'User'),
                    (6, 'Idle Schedule')
            ) _ (
                [run_requested_source],
                [friendly_name]
            )
        )
        SELECT
            a.[job_id],
            run_requested_source = c.[friendly_name],
            a.[run_requested_date],
            a.[start_execution_date],
            a.[last_executed_step_id],
            a.[stop_execution_date],
            b.[message]
        FROM (
            SELECT TOP 1
                [job_id],
                [run_requested_source],
                [run_requested_date],
                [start_execution_date],
                [last_executed_step_id],
                [stop_execution_date],
                [job_history_id]
            FROM
                msdb.dbo.sysjobactivity
            WHERE
                [job_id] = '?'
        ) AS a
        LEFT JOIN msdb.dbo.sysjobhistory AS b ON
            a.[job_history_id] = b.[instance_id]
        LEFT JOIN cteRunSourceIDs AS c ON
            a.[run_requested_source] = c.[run_requested_source];
        """,
        get_job_steps="""
        SELECT
            [step_name],
            [subsystem],
            [database_name]
        FROM
            msdb.dbo.sysjobsteps
        WHERE
            [job_id] = '?'
        ORDER BY
            [step_id] ASC;
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
    """
    class CommandJobs

    Class that handles execution when the user types '%jobs ...' at the command line
    """

    @property
    def argument_parser(self: "CommandJobs") -> ArgumentParser:
        return _command_jobs_arg_parser

    def _display_job_last_run(self: "CommandJobs", last_run: JobLastRunDetails) -> None:
        self.parent.print_message_sql("Last run details:")

        prefixes: List[Tuple[str, str]] = [
            ("run_requested_date", "Request date:"),
            ("run_requested_source", "Request source:"),
            ("is_running", "Running:"),
            ("start_execution_date", "Start date:"),
            ("stop_execution_date", "End date:"),
            ("message", "Message:"),
        ]
        justify_length: int = max(len(prefix_tuple[1]) for prefix_tuple in prefixes)
        for attr_name, prefix in prefixes:
            self.parent.print_info(
                f"    {prefix.ljust(justify_length)} {getattr(last_run, attr_name)}"
            )

        self.parent.print_info()

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
            case "detail":
                self._job_detail(query_set)
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

    def _fetch_job_description(
        self: "CommandJobs", job_id: str, query_set: _JobQuerySet
    ) -> str:
        results: List[Tuple] = self.parent.context.backends.sql.fetch_results_for(
            self.parent.context.backends.sql.make_query(
                query_set.get_job_description.replace("?", job_id.replace("'", "''"))
            )
        )

        if len(results) > 0:
            return str(results[0][0])

        raise UnknownJobException(f"A job with id '{job_id}' was not found")

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

    def _fetch_job_last_run(
        self: "CommandJobs", job_id: str, query_set: _JobQuerySet
    ) -> JobLastRunDetails | None:
        results: List[Tuple] = self.parent.context.backends.sql.fetch_results_for(
            self.parent.context.backends.sql.make_query(
                query_set.get_job_last_run.replace("?", job_id.replace("'", "''"))
            )
        )

        if len(results) > 0:
            return JobLastRunDetails(*results[0])

        return None

    def _fetch_job_steps(
        self: "CommandJobs", job_id: str, query_set: _JobQuerySet
    ) -> List[JobStep]:
        return [
            JobStep(*record_tuple)
            for record_tuple in self.parent.context.backends.sql.fetch_results_for(
                self.parent.context.backends.sql.make_query(
                    query_set.get_job_steps.replace("?", job_id.replace("'", "''"))
                )
            )
        ]

    @staticmethod
    def get_completions(
        word_before_cursor: str, command_tokens: List[str]
    ) -> List[Suggestion]:
        return []

    def _job_detail(self: "CommandJobs", query_set: _JobQuerySet) -> None:
        job_name: str = self.args.job_name
        job_id: str = self._fetch_job_id(job_name, query_set)

        # display the name of the job and a description
        self.parent.print_message_sql(job_name)
        self.parent.print_info(self._fetch_job_description(job_id, query_set))
        self.parent.print_info()

        # get the status of the most recent run
        last_run: JobLastRunDetails = self._fetch_job_last_run(job_id, query_set)
        if last_run is None:
            self.parent.print_info("Unable show details of last job run.")
            return

        self._display_job_last_run(last_run)

        # display all of the job steps
        self.parent.print_message_sql("Steps:")
        for line in self.parent.context.backends.table.construct_table(
            RecordSet(
                columns=["Name", "Subsystem", "Target Database"],
                records=[
                    astuple(job_step)
                    for job_step in self._fetch_job_steps(job_id, query_set)
                ],
            )
        ).splitlines():
            print(f"    {line}")

        self.parent.print_info()

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
