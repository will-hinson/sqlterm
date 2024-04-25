from dataclasses import dataclass


@dataclass
class Suggestion:
    content: str
    position: int
    suffix: str = ""
