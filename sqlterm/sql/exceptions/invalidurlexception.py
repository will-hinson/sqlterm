"""
module sqlterm.sql.exceptions.invalidurlexception

Contains the definition of the InvalidUrlException class, an exception
that is thrown whenever an invalid connection url is provided to a
sql backend method
"""

from .sqlbackendexception import SqlBackendException


class InvalidUrlException(SqlBackendException):
    """
    class InvalidUrlException

    An exception that is thrown whenever an invalid connection url is
    provided to a sql backend method
    """
