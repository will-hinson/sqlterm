from dataclasses import dataclass

from ..prompt.abstract import PromptBackend
from ..sql.abstract import SqlBackend
from ..tables.abstract import TableBackend


@dataclass(frozen=True)
class BackendSet:
    prompt: PromptBackend
    sql: SqlBackend
    table: TableBackend
