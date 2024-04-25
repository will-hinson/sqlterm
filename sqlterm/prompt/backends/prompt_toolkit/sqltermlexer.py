import functools
import os
from typing import Callable, Dict

from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import StyleAndTextTuples
from prompt_toolkit.lexers import Lexer, PygmentsLexer

# pylint: disable=no-name-in-module
from pygments.lexers import (
    BashLexer,
    BatchLexer,
    MySqlLexer,
    PostgresLexer,
    SqlLexer,
    TransactSqlLexer,
)

# pylint: enable=no-name-in-module

from .... import constants
from ....sql.generic.enums import SqlDialect
from ....prompt.abstract import PromptBackend


class SqlTermLexer(Lexer):
    __parent: "PromptBackend"

    dialect_lexers: Dict[SqlDialect, PygmentsLexer]
    default_sql_lexer: PygmentsLexer
    system_lexer: PygmentsLexer

    def __init__(
        self: "SqlTermLexer", parent: "prompttoolkitbackend.PromptToolkitBackend"
    ) -> None:
        self.__parent = parent

        self.default_sql_lexer = PygmentsLexer(SqlLexer)
        self.dialect_lexers = {
            SqlDialect.MYSQL: PygmentsLexer(MySqlLexer),
            SqlDialect.POSTGRES: PygmentsLexer(PostgresLexer),
            SqlDialect.TSQL: PygmentsLexer(TransactSqlLexer),
        }

        if os.name == "nt":
            self.system_lexer = PygmentsLexer(BatchLexer)
        else:
            self.system_lexer = PygmentsLexer(BashLexer)

    def lex_document(
        self: "SqlTermLexer", document: Document
    ) -> Callable[[int], StyleAndTextTuples]:
        match document.text[:1]:
            # ---- shell command ----
            case constants.PREFIX_SHELL_COMMAND:
                # function to override the default lexer get_line() function with one that
                # will return '!' in the first tuple. we do this so that we can pass the
                # document sans '!' to the lexer and get a proper lex result
                def _get_line_override(
                    line_number: int, get_line_func: Callable[[int], StyleAndTextTuples]
                ) -> StyleAndTextTuples:
                    if line_number == 0:
                        return [
                            (
                                "class:shell.command-sigil",
                                constants.PREFIX_SHELL_COMMAND,
                            ),
                            *get_line_func(line_number)[1:],
                        ]

                    return get_line_func(line_number)

                return functools.partial(
                    _get_line_override,
                    get_line_func=self.system_lexer.lex_document(
                        Document(
                            text=" " + document.text[1:],
                            cursor_position=document.cursor_position,
                            selection=document.selection,
                        )
                    ),
                )

            # ---- sqlterm command ----
            case constants.PREFIX_SQLTERM_COMMAND:
                return lambda line_number: [
                    ("class:shell.command-sigil", constants.PREFIX_SQLTERM_COMMAND),
                    (
                        "class:shell.command",
                        document.lines[line_number][
                            len(constants.PREFIX_SQLTERM_COMMAND) :
                        ],
                    ),
                ]

        # otherwise, lex a sql document
        return self._lex_document_sql(document=document)

    def _lex_document_sql(
        self: "SqlTermLexer", document: Document
    ) -> Callable[[int], StyleAndTextTuples]:
        # see if we can use a specific lexer for this context
        if self.__parent.dialect in self.dialect_lexers:
            return self.dialect_lexers[self.__parent.dialect].lex_document(document)

        # otherwise, use the default/generic dialect
        return self.default_sql_lexer.lex_document(document)


# pylint: disable=wrong-import-position
from . import prompttoolkitbackend
