"""
module sqlterm.commands.dataclasses.joblastrundetails

Contains the definition of the JobLastRunDetails class, a dataclass that
represents the status of the last run of a SQL job
"""

from dataclasses import dataclass
from datetime import date


@dataclass
class JobLastRunDetails:
    """
    class JobLastRunDetails

    Dataclass that represents the status of the last run of a SQL job
    """

    # pylint: disable=too-many-instance-attributes

    job_id: str
    run_requested_source: str | None
    run_requested_date: date
    start_execution_date: date | None
    last_executed_step_id: int | None
    stop_execution_date: date | None
    message: str | None
    is_running: bool = None  # type: ignore

    def __post_init__(self: "JobLastRunDetails") -> None:
        self.is_running = self.stop_execution_date is None
