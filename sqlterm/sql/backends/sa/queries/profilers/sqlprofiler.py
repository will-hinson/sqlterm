from abc import ABCMeta
from threading import Thread


class SqlProfiler(metaclass=ABCMeta):
    current_thread: Thread | None = None
    parent: "sabackend.SaBackend"

    def __init__(self: "SqlProfiler", parent: "sabackend.SaBackend") -> None:
        self.parent = parent


from ... import sabackend
