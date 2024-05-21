"""
module sqlterm.commands.exceptions.noaliasexistsexception

Contains the definition of the NoAliasExistsException class which is
thrown when the user attempts to use or modify an alias that has
not been previously created
"""

from ...sqltermexception import SqlTermException


class NoAliasExistsException(SqlTermException):
    """
    class NoAliasExistsException

    An exception thrown when the user attempts to use or modify
    an alias that has not been previously created
    """
