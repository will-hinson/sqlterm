import argparse
import importlib
import os
import pkgutil
from types import ModuleType
from typing import List, Type

from . import constants
from .commands import sqltermcommand, SqlTermCommand
from .commands.exceptions import AliasExistsException, HelpShown, NoAliasExistsException
from .config import Alias, SqlTermConfig
from .context import BackendSet, SqlTermContext
from .prompt.abstract import PromptBackend
from .prompt.exceptions import UserExit
from .sql.abstract import Query, SqlBackend
from .sql.exceptions import SqlException
from .sqltermexception import SqlTermException
from .tables.backends import table_backends_by_name
from .tables.backends.terminaltables import TerminalTablesBackend


class SqlTerm:
    __context: SqlTermContext

    def __init__(
        self: "SqlTerm",
        sql_backend: Type[SqlBackend],
        prompt_backend: Type[PromptBackend],
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
                table=(
                    table_backends_by_name[config.table_backend]
                    if config.table_backend in table_backends_by_name
                    else TerminalTablesBackend
                )(),
            ),
            config_path=config_path,
            config=config,
        )

        # set the table backend and parent for the sql backend
        self.context.backends.prompt.parent = self
        self.context.backends.sql.parent = self
        self.context.backends.sql.table_backend = self.context.backends.table

        # load any plugins that are installed
        self._load_plugins()

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

        # do nothing if the command was an empty one
        if len(command) == 0:
            return

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
            try:
                self.context.backends.prompt.display_info(" KeyboardInterrupt")
            except KeyboardInterrupt:
                ...
        # pylint: disable=broad-exception-caught
        except Exception as exc:
            self.context.backends.prompt.display_exception(exc, unhandled=True)

    def invalidate_completions(self: "SqlTerm") -> None:
        self.context.backends.sql.invalidate_completions()

    def _load_plugin_module(self: "SqlTerm", plugin_module: ModuleType) -> None:
        # try loading custom commands
        if hasattr(plugin_module, "commands"):
            if not isinstance(plugin_module.commands, dict):
                print(
                    f"Unable to fully load plugin module {plugin_module.__name__}: "
                    "commands attribute is not a dict"
                )
                return

            for name, command_class in plugin_module.commands.items():
                # pylint: disable=no-member
                sqltermcommand.available_commands[name] = command_class

        # try loading custom styles
        if hasattr(plugin_module, "styles"):
            if not isinstance(plugin_module.commands, dict):
                print(
                    f"Unable to fully load plugin module {plugin_module.__name__}: "
                    "styles attribute is not a dict"
                )
                return

            if type(self.context.backends.prompt) not in plugin_module.styles:
                return

            for name, style_class in plugin_module.styles[
                type(self.context.backends.prompt)
            ].items():
                self.context.backends.prompt.add_style(name, style_class)

            self.context.backends.prompt.refresh_style()

    def _load_plugins(self: "SqlTerm") -> None:
        # load all modules with the prefix 'sqlterm_'. this pattern comes from
        # https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/
        #
        # pylint: disable=broad-exception-caught
        discovered_plugins: List[ModuleType]
        try:
            discovered_plugins = [
                importlib.import_module(name)
                for _, name, __ in pkgutil.iter_modules()
                if name.startswith("sqlterm_")
            ]
        except Exception as exc:
            self.context.backends.prompt.display_exception(exc, unhandled=True)
            return

        for plugin_module in discovered_plugins:
            self._load_plugin_module(plugin_module)

    def print_info(self: "SqlTerm", message: str = "") -> None:
        self.context.backends.prompt.display_info(message)

    def print_message_sql(self: "SqlTerm", message: str) -> None:
        self.context.backends.prompt.display_message_sql(message)

    def repl(self: "SqlTerm") -> None:
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
                try:
                    self.handle_command(user_command)
                except KeyboardInterrupt:
                    ...

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

    def reset_table_backend(self: "SqlTerm") -> None:
        self.context.backends.table = (
            table_backends_by_name[self.context.config.table_backend]
            if self.context.config.table_backend in table_backends_by_name
            else TerminalTablesBackend
        )()
        self.context.backends.sql.table_backend = self.context.backends.table
        self._flush_config()

    def set_alias_prompt_color(
        self: "SqlTerm", alias_name: str, prompt_color: str
    ) -> None:
        self.context.config.aliases[alias_name].prompt_color = prompt_color
        self._flush_config()

        self.context.backends.prompt.set_prompt_color(prompt_color)

    def set_autoformat(self: "SqlTerm", autoformat_setting: bool) -> None:
        self.context.config.autoformat = autoformat_setting
        self._flush_config()

        self.context.backends.prompt.config.autoformat = autoformat_setting
