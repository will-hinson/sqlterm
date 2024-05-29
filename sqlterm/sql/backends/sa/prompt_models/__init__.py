"""
module sqlterm.sql.backends.sa.prompt_models

Contains the definitions of all SQLAlchemy-specific prompt models. In general,
these are used to prompt the user for a series of answers that can be used to
construct connection strings
"""

from .mssqlpromptmodel import MsSqlPromptModel
from .sqlitepromptmodel import SqlitePromptModel
