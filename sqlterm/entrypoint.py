from .config import SqlTermConfig
from .prompt.backends.prompt_toolkit import PromptToolkitBackend
from .sql.backends.sa import SaBackend
from .sqlterm import SqlTerm
from .tables.backends.terminaltables import TerminalTablesBackend


def main() -> int:
    session: SqlTerm = SqlTerm(
        sql_backend=SaBackend(),
        prompt_backend=PromptToolkitBackend(),
        table_backend=TerminalTablesBackend(),
        config_path=SqlTermConfig.default_path(),
    )
    session.repl()

    return 0
