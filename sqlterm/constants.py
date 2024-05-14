import os
from typing import List, Set

import shellingham

from sqlterm import __version__


def _get_fallback_shell():
    if os.name == "posix":
        return os.environ["SHELL"]
    elif os.name == "nt":
        return os.environ["COMSPEC"]

    raise NotImplementedError(f"OS {os.name!r} support not available")


APPLICATION_NAME: str = __name__[: __name__.index(".")]
APPLICATION_VERSION: str = __version__

COMMAND_SUGGESTION_MAX_DISTANCE: int = 5

CONFIG_VERSION: str = "0.1"

PREFIX_SHELL_COMMAND: str = "!"
PREFIX_SQLTERM_COMMAND: str = "%"

PROGRESS_CHARACTERS: List[str] = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

SHELL_DEFAULT: str
try:
    SHELL_DEFAULT = shellingham.detect_shell()[-1]
except shellingham.ShellDetectionFailure:
    SHELL_DEFAULT = _get_fallback_shell()

SPACES_IN_TAB: int = 4

TREE_VIEW_COLLAPSED_CHAR: str = "▷"
TREE_VIEW_EXPANDED_CHAR: str = "▽"

ANSI_SQL_FUNCTIONS: Set[str] = {
    "ABS()",
    "AVG()",
    "CAST()",
    "CEILING()",
    "COALESCE()",
    "CONCAT()",
    "COUNT()",
    "FLOOR()",
    "LEFT()",
    "LENGTH()",
    "LOWER()",
    "MAX()",
    "MIN()",
    "MOD()",
    "POWER()",
    "RAND()",
    "RANK()",
    "RIGHT()",
    "ROUND()",
    "ROW_NUMBER()",
    "SQRT()",
    "SUBSTR()",
    "SUM()",
    "TRIM()",
    "UPPER()",
}
ANSI_SQL_KEYWORDS: Set[str] = {
    "ALL",
    "ALTER",
    "AND",
    "ANY",
    "AS",
    "BY",
    "CASE",
    "CREATE",
    "DELETE",
    "DISTINCT",
    "DROP",
    "ELSE",
    "END",
    "EXISTS",
    "EXCEPT",
    "FOREIGN",
    "FROM",
    "GROUP",
    "HAVING",
    "IN",
    "INNER",
    "INSERT",
    "INTERSECT",
    "INTO",
    "JOIN",
    "KEY",
    "LEFT",
    "NOT",
    "ON",
    "OR",
    "ORDER",
    "OUTER",
    "OVER",
    "PARTITION",
    "PRIMARY",
    "REFERENCES",
    "RIGHT",
    "SELECT",
    "SET",
    "TABLE",
    "THEN",
    "UNION",
    "UPDATE",
    "VALUES",
    "WHEN",
    "WHERE",
}
