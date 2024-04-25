from dataclasses import dataclass

from .backendset import BackendSet
from ..config import SqlTermConfig


@dataclass(frozen=True)
class SqlTermContext:
    backends: BackendSet
    config: SqlTermConfig
    config_path: str
