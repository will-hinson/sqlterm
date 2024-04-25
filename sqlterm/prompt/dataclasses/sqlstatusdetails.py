from dataclasses import dataclass


@dataclass
class SqlStatusDetails:
    connected: bool
    connection_detail: str | None
    dialect: str | None
