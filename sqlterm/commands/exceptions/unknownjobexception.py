"""
module sqlterm.commands.exceptions.unknownjobexception

Contains the definition of the UnknownJobException class which is
thrown when the user references a job by name that is not recognized
by the remote SQL server
"""

from .commandexception import CommandException


class UnknownJobException(CommandException):
    """
    class UnknownJobException

    An exception thrown when the user references a job by name that
    is not recognized by the remote SQL server
    """
