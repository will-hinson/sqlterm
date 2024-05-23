"""
module sqlterm.sql.generic.recordset

Contains the definition of the RecordSet class, a dataclass that
contains a set of SQL records represents as tuples as well as the
fields that are present in the record
"""

from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class RecordSet:
    """
    class RecordSet

    Dataclass that contains a set of SQL records represents as
    tuples as well as the fields that are present in the record
    """

    columns: List[str]
    records: List[Tuple]
