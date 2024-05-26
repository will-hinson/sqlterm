"""
module sqlterm.prompt.exceptions.userexit

Contains the definition of the UserExit exception class, an exception
thrown whenever the user has performed an expected action that represents
intent to exit sqlterm
"""

from ...sqltermexception import SqlTermException


class UserExit(SqlTermException):
    """
    class UserExit

    An exception thrown whenever the user has performed an expected action
    that represents intent to exit sqlterm
    """
