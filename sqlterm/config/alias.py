"""
module sqlterm.config.alias

Contains the definition of the Alias class, a dataclass that
represents an alias definition in sqlterm
"""

from dataclasses import dataclass


@dataclass
class Alias:
    """
    class Alias

    Dataclass that represents a connection alias defintion
    """

    url: str
    prompt_color: str | None = None
