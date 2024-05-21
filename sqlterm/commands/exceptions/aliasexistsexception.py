"""
module sqlterm.commands.exceptions.aliasexistsexception

Contains the definition of the AliasExistsException class which is
thrown when the user attempts to create an alias with the same
name as one that already exists
"""

from ...sqltermexception import SqlTermException


class AliasExistsException(SqlTermException):
    """
    class AliasExistsException

    An exception thrown when the user attempts to create an alias
    with the same name as one that already exists
    """
