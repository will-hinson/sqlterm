"""
module sqlterm.sql.exceptions.missingmoduleexception

Contains the definition of the MissingModuleException class, an exception that
is thrown whenever a user tries establish a SQL connection for which a
required Python module is not installed
"""

from .dialectexception import DialectException


class MissingModuleException(DialectException):
    """
    class MissingModuleException

    An exception that is thrown whenever a user tries establish a SQL connection
    for which a required Python module is not installed
    """
