import argparse
import os
from typing import NoReturn, Type

from . import constants
from .commands import SqlTermCommand
from .commands.exceptions import AliasExistsException, HelpShown
from .config import Alias, SqlTermConfig
from .context import BackendSet, SqlTermContext
from .prompt.abstract import PromptBackend
from .prompt.exceptions import UserExit
from .sql.abstract import Query, SqlBackend
from .sql.exceptions import SqlException
from .sqltermexception import SqlTermException
from .tables.abstract import TableBackend


class SqlTerm:
    __context: SqlTermContext

    def __init__(
        self: "SqlTerm",
        sql_backend: Type[SqlBackend],
        prompt_backend: Type[PromptBackend],
        table_backend: Type[TableBackend],
        config_path: str,
    ) -> None:
        # try reading a config instance from the provided config file. otherwise, construct
        # a default config
        config: SqlTermConfig | None = SqlTermConfig.from_file(config_path)
        if config is None:
            config = SqlTermConfig.make_default()

        self.__context = SqlTermContext(
            backends=BackendSet(
                prompt=prompt_backend(config),
                sql=sql_backend(),
                table=table_backend(),
            ),
            config_path=config_path,
            config=config,
        )

        # set the table backend and parent for the sql backend
        self.context.backends.prompt.parent = self
        self.context.backends.sql.parent = self
        self.context.backends.sql.table_backend = self.context.backends.table

    def get_command(self: "SqlTerm") -> str:
        return self.context.backends.prompt.get_command()

    @property
    def context(self: "SqlTerm") -> SqlTermContext:
        return self.__context

    def create_alias(self: "SqlTerm", alias_name: str, connection_string: str) -> None:
        if alias_name in self.context.config.aliases:
            raise AliasExistsException(
                f"An alias with the name '{alias_name}' already exists"
            )

        self.context.config.aliases[alias_name] = Alias(connection_string)
        self._flush_config()

        self.context.backends.prompt.display_message_sql(
            f"Created alias '{alias_name}'"
        )

    def _flush_config(self: "SqlTerm") -> None:
        self.context.config.to_file(self.context.config_path)

    def handle_command(self: "SqlTerm", command: str) -> None:
        command = command.strip()

        match command[:1]:
            case constants.PREFIX_SHELL_COMMAND:
                self._handle_command_shell(command[1:])
            case constants.PREFIX_SQLTERM_COMMAND:
                self._handle_command_sqlterm(command[1:])
            case _:
                self._handle_query_sql(command)

    def _handle_command_shell(self: "SqlTerm", command: str) -> int:
        if len(command.strip()) == 0:
            return os.system(constants.SHELL_DEFAULT)

        return os.system(command)

    def _handle_command_sqlterm(self: "SqlTerm", command: str) -> None:
        # pylint: disable=broad-exception-caught
        try:
            SqlTermCommand.from_user_input(command, parent=self).execute()
        except HelpShown:
            # ignore cases where the command showed help to the user
            ...
        except argparse.ArgumentError as ae:
            # remove the class instance that we receive in the argument error and
            # only output the human-readable message
            ae.args = ae.args[1:]
            self.context.backends.prompt.display_exception(ae)
        except SqlTermException as ste:
            self.context.backends.prompt.display_exception(ste)
        except NotImplementedError as nie:
            self.context.backends.prompt.display_exception(nie)
        except Exception as exc:
            self.context.backends.prompt.display_exception(exc, unhandled=True)

    def _handle_query_sql(self: "SqlTerm", query_str: str) -> None:
        # construct a query from the provided string
        sql_backend: SqlBackend = self.context.backends.sql
        user_query: Query = sql_backend.make_query(query_str)

        try:
            sql_backend.execute(user_query)
        except SqlException as sqe:
            self.context.backends.prompt.display_exception(sqe)
        except KeyboardInterrupt:
            self.context.backends.prompt.display_info(" KeyboardInterrupt")
        except Exception as exc:
            self.context.backends.prompt.display_exception(exc, unhandled=True)

    def invalidate_completions(self: "SqlTerm") -> None:
        self.context.backends.sql.invalidate_completions()

    def print_message_sql(self: "SqlTerm", message: str) -> None:
        self.context.backends.prompt.display_message_sql(message)

    def repl(self: "SqlTerm") -> NoReturn:
        user_exited: bool = False

        while not user_exited:
            # try getting a query from the user. if they signal an exit,
            # break out of the loop
            user_command: str
            try:
                user_command = self.get_command()
            except UserExit:
                user_exited = True
                continue

            # execute the command if it wasn't empty
            if len(user_command.strip()) != 0:
                self.handle_command(user_command)

    def remove_alias(self: "SqlTerm", alias_name: str) -> None:
        if alias_name not in self.context.config.aliases:
            raise NoAliasExistsException(
                f"An alias with the name '{alias_name}' does not exist"
            )

        del self.context.config.aliases[alias_name]
        self._flush_config()

        self.context.backends.prompt.display_message_sql(
            f"Removed alias '{alias_name}'"
        )
