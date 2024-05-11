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
        current_dialect: SqlDialect | None = self.parent.context.backends.prompt.dialect

        # check that the current dialect is supported for this command
        if not self.parent.context.backends.sql.connected:
            raise DisconnectedException("No SQL connection is currently established")
        if current_dialect not in _queries_for_dialect:
            raise NotImplementedError(
                f"%edit command not implemented for current SQL dialect '{current_dialect}'"
            )

        job_source_results: List[Tuple] = (
            self.parent.context.backends.sql.fetch_results_for(
                self.parent.context.backends.sql.make_query(
                    _queries_for_dialect[current_dialect].replace(
                        "?", self.args.object_name.replace("'", "''")
                    )
                )
            )
        )
        if len(job_source_results) == 0 or job_source_results[0][0] is None:
            raise SqlQueryException(
                f"Unable to retrieve source for object '{self.args.object_name}'"
            )

        # reshow the prompt containing the source of the object
        self.parent.handle_command(
            self.parent.context.backends.prompt.get_command(job_source_results[0][0])
        )
