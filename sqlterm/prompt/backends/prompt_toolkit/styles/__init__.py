"""
module sqlterm.prompt.backends.prompt_toolkit.styles

Contains the definitions of all custom built-in Pygments styles made available to
the user via the prompt_toolkit backend
"""

from typing import Dict, Type

from pygments.style import Style

from .tokyonightdark import TokyoNightDark

sqlterm_styles: Dict[str, Type[Style]] = {"tokyo-night-dark": TokyoNightDark}
