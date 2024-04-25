from dataclasses import dataclass
from typing import Set

from ..enums import SqlDialect
from .sqlobject import SqlObject


@dataclass
class SqlStructure:
    dialect: SqlDialect
    objects: Set[SqlObject]
    keywords: Set[SqlObject]
    builtin_types: Set[SqlObject]

    def flatten(self: "SqlStructure") -> Set[SqlObject]:
        flattened_children: Set[SqlObject] = set()

        for child in self.objects:
            flattened_children.add(child)
            flattened_children |= child.flatten()

        return flattened_children | self.keywords | self.builtin_types
