"""
module sqlterm.commands.exceptions.unknowncommandexception

Contains the definition of the UnknownCommandException class which is
thrown when the user attempts to invoke a builtin command using the
'%' sigil but the name of the command is not known
"""

from .commandexception import CommandException


class UnknownCommandException(CommandException):
    """
    class UnknownCommandException

    An exception thrown when the user attempts to invoke a builtin command
    using the '%' sigil but the name of the command is not known
    """
