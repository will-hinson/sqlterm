import math
import shutil
from threading import Thread
import time
from typing import List, Tuple

from .... import constants


def _human_readable_duration_hms(seconds: float) -> str:
    return (
        f"{int(seconds // (60 * 60))}".rjust(2, "0")
        + ":"
        + f"{int(seconds // 60) % 60}".rjust(2, "0")
        + ":"
        + f"{int(seconds) % 60}".rjust(2, "0")
    )


def _human_readable_duration(seconds: float) -> str:
    day_length: int = 60 * 60 * 24

    if seconds < 60:
        return f"{math.floor(seconds * 10) / 10}s"
    if seconds < day_length:
        return _human_readable_duration_hms(seconds)

    return f"{int(seconds // day_length)} days " + _human_readable_duration_hms(
        seconds % day_length
    )


class SaSpoolMonitor(Thread):
    __display_progress: bool
    __parent: "sabackend.SaBackend"
    __spool: List[Tuple]
    __stopped: bool

    __load_char_offset: int

    done: bool

    def __init__(
        self: "SaSpoolMonitor",
        spool: List[Tuple],
        parent: "sabackend.SaBackend",
        display_progress: bool,
    ) -> None:
        super().__init__()

        self.__display_progress = display_progress
        self.__parent = parent
        self.__spool = spool

        self.__load_char_offset = 0
        self.__stopped = False
        self.done = False

    @property
    def parent(self: "SaSpoolMonitor") -> "sabackend.SaBackend":
        return self.__parent

    def run(self: "SaSpoolMonitor") -> None:
        self.parent.parent.context.backends.prompt.hide_cursor()

        start_time: float = time.time()
        tab_sep: str = " " * constants.SPACES_IN_TAB

        while not self.__stopped:
            if self.__display_progress:
                # output the current time elapsed and the number of records received
                self.parent.display_progress(
                    constants.PROGRESS_CHARACTERS[self.__load_char_offset],
                    " ",
                    _human_readable_duration(time.time() - start_time),
                    tab_sep,
                    f"{len(self.spool):,} row{'s' if len(self.spool) != 1 else ''}",
                    "" if not self.done else " \u2713",
                )
                self.__load_char_offset = (self.__load_char_offset + 1) % len(
                    constants.PROGRESS_CHARACTERS
                )

            time.sleep(0.1)

        # clear the line we're currently on
        print("\r", end="")
        print(" " * (shutil.get_terminal_size().columns - 1), end="")
        print("\r", end="")

        self.parent.parent.context.backends.prompt.show_cursor()

    @property
    def spool(self: "SaSpoolMonitor") -> List[Tuple]:
        return self.__spool

    def stop(self: "SaSpoolMonitor") -> None:
        self.__stopped = True


# pylint: disable=wrong-import-position
from . import sabackend
