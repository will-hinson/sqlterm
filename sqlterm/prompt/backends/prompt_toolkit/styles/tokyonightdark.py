"""
module sqlterm.prompt.backends.prompt_toolkit.styles.tokyonightdark

Contains the definition of the 'tokyo-night-dark' custom built-in color scheme
"""

from pygments.style import Style
from pygments.token import Token


class TokyoNightDark(Style):
    # pylint: disable=missing-class-docstring, too-few-public-methods

    styles = {
        Token: "",
        Token.Comment: "#646B8A",
        Token.Keyword: "#89DDFF",
        Token.Keyword.Type: "#89DDFF",
        Token.Literal.Number: "#F7768E",
        Token.Literal.Number.Float: "#F7768E",
        Token.Literal.String.Single: "#85D0B7",
        Token.Literal.String.Symbol: "#BB9AF7",
        Token.Name: "#DFE4FA",
        Token.Name.Builtin: "#89DDFF",
        Token.Name.Class: "#0DB9D7",
        Token.Name.Function: "#7AA2F7 italic",
        Token.Name.Label: "#e0af68 bold italic",
        Token.Name.Variable: "#DFE4FA italic",
        Token.Operator: "#BB9AF7",
        Token.Operator.Word: "#BB9AF7",
        Token.Punctuation: "#A9B1D6",
        Token.Text: "#DFE4FA",
        Token.Text.Whitespace: "",
    }
