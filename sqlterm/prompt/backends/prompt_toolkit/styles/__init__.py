from typing import Dict, Type

from pygments.style import Style

from .tokyonightdark import TokyoNightDark

sqlterm_styles: Dict[str, Type[Style]] = {"tokyo-night-dark": TokyoNightDark}
