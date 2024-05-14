from dataclasses import dataclass
from typing import List

from ...sql.generic.dataclasses import SqlObject


@dataclass
class SqlReference:
    hierarchy: List[SqlObject]
