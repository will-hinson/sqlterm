from typing import Dict, Type

from pygments.style import Style

from .tokyonight import TokyoNight

sqlterm_styles: Dict[str, Type[Style]] = {"tokyo-night": TokyoNight}
