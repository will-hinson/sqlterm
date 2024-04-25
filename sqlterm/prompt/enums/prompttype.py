from enum import auto, Enum
from typing import Dict, Type


class PromptType(Enum):
    BASIC = auto()
    ENUM = auto()
    PASSWORD = auto()
    YES_NO = auto()


prompt_type_return_types: Dict[PromptType, Type] = {
    PromptType.BASIC: str,
    PromptType.ENUM: Type[Enum],
    PromptType.PASSWORD: str,
    PromptType.YES_NO: bool,
}
