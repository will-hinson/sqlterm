from abc import ABCMeta, abstractmethod

from ...sql.generic import RecordSet


class TableBackend(metaclass=ABCMeta):
    def __init__(self: "TableBackend") -> None: ...

    @abstractmethod
    def construct_table(self: "TableBackend", record_set: RecordSet) -> str: ...
