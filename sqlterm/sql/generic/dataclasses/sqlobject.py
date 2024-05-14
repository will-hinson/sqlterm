from dataclasses import dataclass
from typing import Set

from ..enums import SqlObjectType


@dataclass
class SqlObject:
    name: str
    type: SqlObjectType
    children: Set["SqlObject"]
    builtin: bool = False
    is_alias: bool = False

    def flatten(self: "SqlObject") -> Set["SqlObject"]:
        flattened_children: Set[SqlObject] = set()

        for child in self.children:
            flattened_children.add(child)
            flattened_children |= child.flatten()

        return flattened_children

    def __hash__(self: "SqlObject") -> int:
        return hash(
            f"{self.name}{self.type}{sum(hash(child) for child in self.children)}{self.is_alias}"
        )
