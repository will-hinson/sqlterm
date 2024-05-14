from argparse import ArgumentParser
from typing import Dict, List, Tuple

from . import sqltermcommand
from .. import constants
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

        # reshow the prompt containing the source of the object
        self.parent.handle_command(
            self.parent.context.backends.prompt.get_command(object_source)
        )

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
