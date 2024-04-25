from sqlalchemy import Connection

from .....backends.sa import SaBackend, SaQuery
from .querymanager import QueryManager


class MySqlManager(QueryManager):
    def __init__(
        self: "MySqlManager", connection: Connection, target_query: SaQuery, parent
    ) -> None:
        super().__init__(connection, target_query, parent)
