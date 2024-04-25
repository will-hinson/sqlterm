from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class RecordSet:
    columns: List[str]
    records: List[Tuple]
