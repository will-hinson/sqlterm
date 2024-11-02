"""
module sqlterm.commands.exceptions.invalidargumentexception

Contains the definition of the InvalidArgumentException class which is
thrown when the user provides an invalid argument to a command
"""

from .commandexception import CommandException


class InvalidArgumentException(CommandException):
    """
    class InvalidArgumentException

    An exception thrown when the user provides an invalid argument
    to a command
    """
