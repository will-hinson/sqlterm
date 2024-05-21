"""
module sqlterm.commands.dataclasses.jobstatusrecord

Contains the definition of the JobStatusRecord dataclass. All records
returned by the '%jobs list' command are marshalled into instances of
this class then displayed
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class JobStatusRecord:
    """
    class JobStatusRecord

    All records returned by the '%jobs list' command are marshalled into instances of
    this class then displayed
    """

    # pylint: disable=too-many-instance-attributes

    job_id: str
    name: str
    description: str
    category: str
    step_count: int
    is_enabled: bool
    last_run_datetime: datetime | None
    last_run_status: str | None
    next_run_datetime: datetime | None
    is_running: bool
