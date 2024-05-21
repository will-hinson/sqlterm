from dataclasses import dataclass
from datetime import datetime


@dataclass
class SqlJob:
    # pylint: disable=too-many-instance-attributes

    id: str
    name: str
    description: str
    category: str
    is_running: bool
    is_enabled: bool
    last_run: datetime
    next_run: datetime
