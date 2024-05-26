"""
module sqlterm.sqltermexception

Contains the definition of the SqlTermException class, the parent of all
exceptions directly thrown by SqlTerm and its backend classes
"""


class SqlTermException(RuntimeError):
    """
    class SqlTermException

    The parent class of all exceptions directly thrown by SqlTerm
    and its backend classes
    """
