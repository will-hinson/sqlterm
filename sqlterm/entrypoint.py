"""
module sqlterm.entrypoint

Contains the definition of the main() method that is invoked when
sqlterm is run directly as a module from the command line
"""

from .config import SqlTermConfig
from .prompt.backends.prompt_toolkit import PromptToolkitBackend
from .sql.backends.sa import SaBackend
from .sqlterm import SqlTerm
from .tables.backends.terminaltables import TerminalTablesBackend


def main() -> int:
    """
    Starts an interactive sqlterm session on the current terminal

    Args:
        Nothing

    Returns:
        int: Exit code to return to be returned to the system

    Raises:
        Nothing
    """

    session: SqlTerm = SqlTerm(
        sql_backend=SaBackend,
        prompt_backend=PromptToolkitBackend,
        table_backend=TerminalTablesBackend,
        config_path=SqlTermConfig.default_path(),
    )
    session.repl()

    return 0
