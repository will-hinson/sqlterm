"""
module sqlterm.context.sqltermcontext

Contains the definition of the SqlTermContext dataclass which contains
all of the required backend classes and configuration details for an
individual sqlterm session
"""

from dataclasses import dataclass

from .backendset import BackendSet
from ..config import SqlTermConfig


@dataclass(frozen=True)
class SqlTermContext:
    """
    class SqlTermContext

    Dataclass which contains all of the required backend classes and
    configuration details for an individual sqlterm session
    """

    backends: BackendSet
    config: SqlTermConfig
    config_path: str
