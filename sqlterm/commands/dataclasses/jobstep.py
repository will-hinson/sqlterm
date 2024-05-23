from dataclasses import dataclass


@dataclass
class JobStep:
    step_name: str
    subsystem: str
    database_name: str
