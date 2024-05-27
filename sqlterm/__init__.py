"""
module sqlterm.__init__

Contains the import of the SqlTerm class that is used in sqlterm.entrypoint to start
a user session. Also contains definitions that indicate the current version of SqlTerm.
"""

__version_info__: tuple[int, ...] = (0, 2, 0)
__version__: str = ".".join(map(str, __version_info__))

from .sqlterm import SqlTerm
