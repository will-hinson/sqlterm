"""
module sqlterm.context.backendset

Contains the definition of the BackendSet dataclass which stores a set
of backend classes that an individual sqlterm session depends on
"""

from dataclasses import dataclass

from ..prompt.abstract import PromptBackend
from ..sql.abstract import SqlBackend
from ..tables.abstract import TableBackend


@dataclass(frozen=True)
class BackendSet:
    """
    class BackendSet

    Dataclass which stores a set of backend classes that an individual
    sqlterm session depends on
    """

    prompt: PromptBackend
    sql: SqlBackend
    table: TableBackend
