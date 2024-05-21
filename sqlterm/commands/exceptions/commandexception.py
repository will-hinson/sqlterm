"""
module sqlterm.commands.exceptions.commandexception

Contains the definition of the CommandException class which is the parent
class of all exceptions that can be thrown directly by commands.
"""

from ...sqltermexception import SqlTermException


class CommandException(SqlTermException):
    """
    class CommandException

    Parent class of all exceptions that can be thrown directly by commands.
    """
