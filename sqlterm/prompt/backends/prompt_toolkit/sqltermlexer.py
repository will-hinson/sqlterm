import functools
import os
from typing import Callable, Dict, List

from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import StyleAndTextTuples
from prompt_toolkit.lexers import Lexer, PygmentsLexer
from pygments.lexers.sql import MySqlLexer, PostgresLexer, SqlLexer, TransactSqlLexer
from pygments.lexers.shell import BashLexer, BatchLexer
from pygments.token import String, Token

from .... import constants
from ....sql.generic.enums import SqlDialect
from ....prompt.abstract import PromptBackend


class _CustomAnsiSqlLexer(SqlLexer):
    ...


class _CustomMySqlLexer(MySqlLexer):
    ...


class _CustomPostgresLexer(PostgresLexer):
    ...


class _CustomTransactSqlLexer(TransactSqlLexer):
    ...


class SqlTermLexer(Lexer):
    __parent: "PromptBackend"

    dialect_lexers: Dict[SqlDialect, PygmentsLexer]
    default_sql_lexer: PygmentsLexer
    system_lexer: PygmentsLexer

    def __init__(
        self: "SqlTermLexer", parent: "prompttoolkitbackend.PromptToolkitBackend"
    ) -> None:
        self.__parent = parent

        # hotpatch the sql lexers with a custom class for double-quoted object names. for
        # whatever reason, the default can lead to double-quoted strings being rendered in
        # a really ugly color. we change them to be single-quoted strings functionally
        for custom_type, base_type in {
            _CustomAnsiSqlLexer: SqlLexer,
            _CustomMySqlLexer: MySqlLexer,
            _CustomPostgresLexer: PostgresLexer,
            _CustomTransactSqlLexer: TransactSqlLexer,
        }.items():
            custom_type.tokens["root"] = list(
                filter(
                    lambda token_tuple: token_tuple[-1] != Token.Literal.String.Symbol,
                    base_type.tokens["root"],
                )
            ) + [
                (r'"(""|[^"])*"', String.Single),
            ]

        self.default_sql_lexer = PygmentsLexer(_CustomAnsiSqlLexer)
        self.dialect_lexers = {
            SqlDialect.MYSQL: PygmentsLexer(_CustomMySqlLexer),
            SqlDialect.POSTGRES: PygmentsLexer(PostgresLexer),
            SqlDialect.TSQL: PygmentsLexer(_CustomTransactSqlLexer),
        }

        if os.name == "nt":
            self.system_lexer = PygmentsLexer(BatchLexer)
        else:
            self.system_lexer = PygmentsLexer(BashLexer)

    def lex_document(
        self: "SqlTermLexer", document: Document
    ) -> Callable[[int], StyleAndTextTuples]:
        leading_whitespace: str = document.text[
            : len(document.text) - len(document.text.lstrip())
        ]

        match document.text.strip()[:1]:
            # ---- shell command ----
            case constants.PREFIX_SHELL_COMMAND:
                # function to override the default lexer get_line() function with one that
                # will return '!' in the first tuple. we do this so that we can pass the
                # document sans '!' to the lexer and get a proper lex result
                def _get_line_override(
                    line_number: int, get_line_func: Callable[[int], StyleAndTextTuples]
                ) -> StyleAndTextTuples:
                    command_tokens: List[str] = self._shell_split(
                        document.lines[line_number][
                            len(leading_whitespace)
                            + len(constants.PREFIX_SQLTERM_COMMAND) :
                        ]
                    )

                    if line_number == 0:
                        return [
                            ("", leading_whitespace),
                            (
                                "class:shell.command-sigil",
                                constants.PREFIX_SHELL_COMMAND,
                            ),
                            (
                                "class:shell.command",
                                command_tokens[0] if len(command_tokens) > 0 else "",
                            ),
                            *(
                                ("class:shell.command-args", token)
                                for token in command_tokens[1:]
                            ),
                        ]

                    return get_line_func(line_number)

                return functools.partial(
                    _get_line_override,
                    get_line_func=self.system_lexer.lex_document(
                        Document(
                            text=leading_whitespace
                            + " "
                            + document.text[len(leading_whitespace) + 1 :],
                            cursor_position=document.cursor_position,
                            selection=document.selection,
                        )
                    ),
                )

            # ---- sqlterm command ----
            case constants.PREFIX_SQLTERM_COMMAND:

                def _get_line_sqlterm_command(line_number: int) -> StyleAndTextTuples:
                    if line_number == 0:
                        command_tokens: List[str] = self._shell_split(
                            document.lines[line_number][
                                len(leading_whitespace)
                                + len(constants.PREFIX_SQLTERM_COMMAND) :
                            ]
                        )

                        return [
                            ("", leading_whitespace),
                            (
                                "class:shell.command-sigil",
                                constants.PREFIX_SQLTERM_COMMAND,
                            ),
                            (
                                "class:shell.command",
                                command_tokens[0] if len(command_tokens) > 0 else "",
                            ),
                            *(
                                ("class:shell.command-args", token)
                                for token in command_tokens[1:]
                            ),
                        ]

                    return [("class:shell.command-args", document.lines[line_number])]

                return _get_line_sqlterm_command

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

    def _shell_split(self: "SqlTermLexer", command: str) -> List[str]:
        """
        Performs a shell split that preserves spaces between tokens. This is
        so that we can use the tokens in formatting user input.

        Args:
            command (str): The command to lex

        Returns:
            List[str]: The tokens contained within the command string

        Raises:
            Nothing
        """

        tokens: List[str] = []
        current_token: str = ""

        position: int = 0
        in_quotes: bool = False
        in_whitespace: bool = False

        while position < len(command):
            match command[position]:
                case "\n" | " " | "\t":
                    if not in_quotes and len(current_token) > 0:
                        tokens.append(current_token)
                        current_token = ""

                    if not in_quotes:
                        in_whitespace = True
                case '"':
                    if position + 1 < len(command) and command[position + 1] == '"':
                        current_token += '"'
                        position += 1
                    else:
                        if not in_quotes and len(current_token) > 0:
                            tokens.append(current_token)
                            current_token = ""

                        in_quotes = not in_quotes
                case _:
                    if in_whitespace:
                        tokens.append(current_token)
                        current_token = ""
                        in_whitespace = False

            current_token += command[position]
            position += 1

        if len(current_token) > 0:
            tokens.append(current_token)

        return tokens


# pylint: disable=wrong-import-position
from . import prompttoolkitbackend
