"""
module sqlterm.commands.dataclasses.jobstep

Contains the definition of the JobStep class, a dataclass that represents
an individual step in a SQL job
"""

from dataclasses import dataclass


@dataclass
class JobStep:
    """
    class JobStep

    Dataclass that represents an individual step in a SQL job
    """

    step_name: str
    subsystem: str
    database_name: str
