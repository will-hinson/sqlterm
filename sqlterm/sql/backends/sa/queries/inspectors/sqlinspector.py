from abc import ABCMeta, abstractmethod
from threading import Thread
import warnings


class SqlInspector(Thread, metaclass=ABCMeta):
    __parent: "sabackend.SaBackend"

    def __init__(self: "SqlInspector", parent: "sabackend.SaBackend") -> None:
        super().__init__()

        self.daemon = True
        self.__parent = parent

    @property
    def parent(self: "SqlInspector") -> "sabackend.SaBackend":
        return self.__parent

    @abstractmethod
    def refresh_structure(self: "SqlInspector") -> None:
        ...

    def run(self: "SqlInspector") -> None:
        # pylint: disable=broad-exception-caught
        try:
            self.refresh_structure()
        except Exception as exc:
            # fail with only a warning since this is a background job
            warnings.warn(f"{type(self).__name__}: {type(exc).__name__}: {exc}")


# pylint: disable=wrong-import-position
from ... import sabackend
