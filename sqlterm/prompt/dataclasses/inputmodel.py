from dataclasses import dataclass
from typing import Callable, List

from ..enums import PromptType
from .suggestion import Suggestion


@dataclass
class InputModel:
    prompt: str
    type: PromptType
    validator: Callable[[str], str | None] | None = None
    completer: Callable[[str, str, int], List[Suggestion]] | None = None
