"""
module sqlterm.prompt.dataclasses.inputmodel

Contains the definition of the InputModel dataclass, a dataclass used by a prompt
backend to prompt the user for a specific type of information and validate that
the input buffer matches a set of criteria.
"""

from dataclasses import dataclass
from typing import Callable, List

from ..enums import PromptType
from .suggestion import Suggestion


@dataclass
class InputModel:
    """
    class InputModel

    A dataclass used by a prompt backend to prompt the user for a specific type
    of information and validate that the input buffer matches a set of criteria.
    """

    prompt: str
    type: PromptType
    validator: Callable[[str], str | None] | None = None
    completer: Callable[[str, str, int], List[Suggestion]] | None = None
