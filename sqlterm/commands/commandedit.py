"""
module sqlterm.commands.commandedit

Contains all definitions for the CommandEdit class which handles
execution when the user types '%edit ...' at the command line
"""

from argparse import ArgumentParser
import re
from typing import Dict, List, Tuple

from . import sqltermcommand
from .. import constants
from ..prompt.dataclasses import Suggestion
from ..sql.exceptions import DisconnectedException, SqlQueryException
from ..sql.generic.enums import SqlDialect

ArgumentParser.edit = sqltermcommand.SqlTermCommand.default_exit  # type: ignore
_command_edit_arg_parser: ArgumentParser = ArgumentParser(
    add_help=False,
    exit_on_error=False,
    prog=f"{constants.PREFIX_SQLTERM_COMMAND}edit",
    description="Recalls the source of the specified database object for editing",
)
_command_edit_arg_parser.add_argument(
    "object_name",
    type=str,
    help="The name of the object (i.e., procedure or function) to recall",
)

_queries_for_dialect: Dict[SqlDialect, str] = {
    SqlDialect.POSTGRES: """
    SELECT
        COALESCE(
            pg_get_constraintdef(to_regclass('?')::oid),
            pg_get_functiondef(to_regclass('?')::oid),
            pg_get_indexdef(to_regclass('?')::oid),
            pg_get_ruledef(to_regclass('?')::oid),
            pg_get_triggerdef(to_regclass('?')::oid),
            CONCAT(
                'CREATE OR REPLACE VIEW ? AS\n',
                pg_get_viewdef(to_regclass('?')::oid)
            )
        );
    """,
    SqlDialect.SQLITE: """
        SELECT
            sql
        FROM
            sqlite_master
        WHERE
            name = '?';
    """,
    SqlDialect.TSQL: """
        SELECT
            OBJECT_DEFINITION(
                OBJECT_ID(
                    '?'
                )
            );
    """,
}


class CommandEdit(sqltermcommand.SqlTermCommand):
    """
    class CommandEdit

    Class that handles execution when the user types '%edit ...' at the command line
    """

    @property
    def argument_parser(self: "CommandEdit") -> ArgumentParser:
        return _command_edit_arg_parser

    def execute(self: "CommandEdit") -> None:
        if not self.parent.context.backends.sql.connected:
            raise DisconnectedException("No SQL connection is currently established")

        current_dialect: SqlDialect | None = self.parent.context.backends.prompt.dialect
        object_source: str | None = self._get_source(current_dialect)

        # check if we were actually able to get object source
        if object_source is None:
            raise SqlQueryException(
                f"Unable to retrieve source for object '{self.args.object_name}'"
            )

        # strip carriage returns
        object_source = "\n".join(
            line if len(line) < 1 or line[-1:] != "\r" else line[:-1]
            for line in object_source.splitlines()
        )

        # reshow the prompt containing the source of the object
        self.parent.handle_command(
            self.parent.context.backends.prompt.get_command(object_source)
        )

    @staticmethod
    def get_completions(
        parent, word_before_cursor: str, command_tokens: List[str]
    ) -> List[Suggestion]:
        return []

    def _get_source(self: "CommandEdit", current_dialect: SqlDialect) -> str | None:
        if current_dialect in _queries_for_dialect:
            object_source_results: List[Tuple] = (
                self.parent.context.backends.sql.fetch_results_for(
                    self.parent.context.backends.sql.make_query(
                        _queries_for_dialect[current_dialect].replace(
                            "?", self.args.object_name.replace("'", "''")
                        )
                    )
                )
            )

            if len(object_source_results) == 0 or object_source_results[0][0] is None:
                return None

            return object_source_results[0][0]

        match current_dialect:
            case SqlDialect.MYSQL:
                return self._get_source_mysql()
            case SqlDialect.ORACLE:
                return self._get_source_oracle()
            case _:
                raise NotImplementedError(
                    f"%edit command not implemented for current SQL dialect '{current_dialect}'"
                )

    def _get_source_mysql(self: "CommandEdit") -> str | None:
        # try a number of different queries to get the object source
        for query in (
            f"SHOW CREATE {object_type} ?;"
            for object_type in (
                "DATABASE",
                "EVENT",
                "FUNCTION",
                "PROCEDURE",
                "TABLE",
                "TRIGGER",
                "USER",
                "VIEW",
            )
        ):
            try:
                object_source_results: List[Tuple] = (
                    self.parent.context.backends.sql.fetch_results_for(
                        self.parent.context.backends.sql.make_query(
                            query.replace("?", self.args.object_name)
                        )
                    )
                )

                if (
                    len(object_source_results) > 0
                    and object_source_results[0][1] is not None
                ):
                    return object_source_results[0][1]

            except SqlQueryException:
                ...

        # if we failed to find the source for the object, return None
        return None

    def _get_source_oracle(self: "CommandEdit") -> str | None:
        schema_name: str | None = None
        object_name: str
        full_name: str = self.args.object_name

        # Check if the fullname contains a dot indicating a schema and object name
        if "." in full_name:
            # Handle quoted identifiers
            if re.match(r'^".*"\.".*"$', full_name):
                schema_name = re.match(r'^"([^"]+)"', full_name).group(1)
                object_name = re.search(r'\."([^"]+)"$', full_name).group(1)
            else:
                # Handle unquoted identifiers
                schema_name, object_name = full_name.split(".")
        else:
            # If no schema was provided, only parse out the object name
            object_name = re.search(r'\."([^"]+)"$', full_name).group(1)

        object_source_results: List[Tuple] = (
            self.parent.context.backends.sql.fetch_results_for(
                self.parent.context.backends.sql.make_query(
                    """
                    WITH cteSourceText (TEXT) AS (
                        SELECT
                            TEXT
                        FROM
                            ALL_SOURCE
                        WHERE
                            OWNER = 'schema?'
                            AND NAME = 'object_name?'
                        ORDER BY
                            LINE ASC
                    )
                    SELECT
                        TEXT
                    FROM
                        cteSourceText
                    
                    UNION ALL

                    SELECT
                        CONCAT(
                            'CREATE OR REPLACE VIEW full_name? AS\n',
                            TEXT_VC
                        )
                    FROM
                        ALL_VIEWS
                    WHERE
                        OWNER = 'schema?'
                        AND VIEW_NAME = 'object_name?'
                    """.replace(
                        "schema?", schema_name.replace("'", "''").upper()
                    )
                    .replace("object_name?", object_name.replace("'", "''").upper())
                    .replace(
                        "full_name?",
                        '"'
                        + schema_name.replace('"', '""')
                        + '"."'
                        + object_name.replace('"', '""')
                        + '"',
                    )
                    if schema_name is not None
                    else """
                    WITH cteSourceText (TEXT) AS (
                        SELECT
                            TEXT
                        FROM
                            ALL_SOURCE
                        WHERE
                            NAME = 'object_name?'
                        ORDER BY
                            LINE ASC
                    )
                    SELECT
                        TEXT
                    FROM
                        cteSourceText
                    
                    UNION ALL

                    SELECT
                        CONCAT(
                            'CREATE OR REPLACE full_name? AS\n',
                            TEXT_VC
                        )
                    FROM
                        ALL_VIEWS
                    WHERE
                        VIEW_NAME = 'object_name?'
                    """.replace(
                        "object_name?", object_name.replace("'", "''").upper()
                    ).replace(
                        "full_name?",
                        '"' + object_name.replace('"', '""') + '"',
                    )
                )
            )
        )

        # reconstruct the source from the results of the query
        source: str = "".join(record[0] for record in object_source_results)

        # if the source wasn't blank/only whitespace, return it
        if len(source.strip()) > 0:
            return source

        # otherwise, we didn't get any valid source
        return None
