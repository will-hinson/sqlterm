__version_info__: tuple[int, ...] = (0, 1, 0)
__version__: str = ".".join(map(str, __version_info__))

from .sqlterm import SqlTerm
