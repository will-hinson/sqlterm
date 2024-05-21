"""
module sqlterm.commands.exceptions.helpshown

Contains the definitions of the HelpShown exception, an
exception class thrown whenever command usage or other help
information was shown to the user and the requested command
did not actually run
"""

from .commandexception import CommandException


class HelpShown(CommandException):
    """
    class HelpShown

    An exception class thrown whenever command usage or other help
    information was shown to the user and the requested command did not
    actually run
    """
