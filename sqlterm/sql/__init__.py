"""
module sqlterm.sql

Contains all submodules and class definitions related to
executing SQL queries in sqlterm. This includes all backend
classes that supervise query execution as well as abstract/
generic classes that represent SQL objects across dialects
"""

from . import abstract
from . import backends
from . import exceptions
from . import generic
