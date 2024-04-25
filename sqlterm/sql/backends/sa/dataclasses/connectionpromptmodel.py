from dataclasses import dataclass
from typing import Callable, List

from sqlalchemy.engine import URL

from .....prompt.dataclasses import InputModel


@dataclass
class ConnectionPromptModel:
    input_models: List[InputModel]
    url_factory: Callable[[List[str]], URL]
