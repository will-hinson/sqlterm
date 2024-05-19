from dataclasses import dataclass
from datetime import datetime


@dataclass
class JobStatusRecord:
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
