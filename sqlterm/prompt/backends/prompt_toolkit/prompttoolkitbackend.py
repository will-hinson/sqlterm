import functools
import traceback
from typing import Any, Callable, Dict, Iterable, List, Tuple

from prompt_toolkit import print_formatted_text, prompt, PromptSession, shortcuts
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout.processors import Processor, TabsProcessor
from prompt_toolkit.styles import (
    BaseStyle,
    merge_styles,
    Style,
    style_from_pygments_cls,
)
from prompt_toolkit.validation import Validator, ValidationError
from pygments.styles import get_style_by_name
import sqlparse

from .... import constants
from ...abstract.promptbackend import PromptBackend
from .completers import DefaultCompleter
from ...dataclasses import InputModel, SqlStatusDetails, Suggestion
from ...enums import PromptType
from ...exceptions import UserExit
from ....sql.generic.dataclasses import SqlStructure
from ....sql.generic.enums.sqldialect import SqlDialect
from .sqltermlexer import SqlTermLexer


class _InputModelCompleter(Completer):
    __completer_func: Callable[[str, str, int], List[Suggestion]] | None

    def __init__(
        self: "_InputModelCompleter",
        completer_func: Callable[[str, str, int], List[Suggestion]] | None,
    ) -> None:
        super().__init__()

        self.__completer_func = completer_func

    def get_completions(self: "_InputModelCompleter", document: Document, _):
        if self.__completer_func is None:
            return []

        word_before_cursor = document.get_word_before_cursor()
        input_model_suggestions: List[Suggestion] = self.__completer_func(
            document.text, word_before_cursor, document.cursor_position_col
        )

        return [
            Completion(
                suggestion.content,
                start_position=suggestion.position,
                display_meta=suggestion.suffix,
            )
            for suggestion in input_model_suggestions
        ]


class _InputModelValidator(Validator):
    __validate_func: Callable[[str], str | None] | None

    def __init__(
        self: "_InputModelValidator", validate_func: Callable[[str], str | None] | None
    ) -> None:
        self.__validate_func = validate_func

    def validate(self: "_InputModelValidator", document: Document) -> None:
        if self.__validate_func is not None:
            if (error_message := self.__validate_func(document.text)) is not None:
                raise ValidationError(document.cursor_position, message=error_message)


class PromptToolkitBackend(PromptBackend):
    __completer: DefaultCompleter
    __lexer: SqlTermLexer
    __session: PromptSession
    __current_statement_index: int

    def __init__(self: "PromptToolkitBackend", *args: Tuple, **kwargs: Dict) -> None:
        super().__init__()

        self.__completer = DefaultCompleter()
        self.__lexer = self._default_lexer

        self.__session = PromptSession(
            *args,  # type: ignore
            bottom_toolbar=functools.partial(type(self)._get_bottom_toolbar, self=self),
            input_processors=self._default_input_processors,
            key_bindings=self._default_key_bindings,
            lexer=self.__lexer,
            multiline=True,
            prompt_continuation=self._prompt_continuation,  # type: ignore
            style=merge_styles(
                [
                    self._default_style,
                    style_from_pygments_cls(get_style_by_name("dracula")),
                ]
            ),
            completer=self.__completer,
            **kwargs,
        )
        self.__current_statement_index = 0
        shortcuts.clear()

    def change_dialect(self: "PromptToolkitBackend", dialect: SqlDialect) -> None:
        self._dialect = dialect

    def clear_completions(self: "PromptToolkitBackend") -> None:
        self.__completer.clear_completions()

    @property
    def _default_input_processors(self: "PromptToolkitBackend") -> List[Processor]:
        return [TabsProcessor()]

    @property
    def _default_key_bindings(self: "PromptToolkitBackend") -> KeyBindings:
        bindings: KeyBindings = KeyBindings()

        def insert_newline(buffer: Buffer) -> None:
            if buffer.document.current_line_after_cursor:
                # When we are in the middle of a line. Always insert a newline.
                buffer.insert_text("\n")
            else:
                current_line: str = buffer.document.current_line_before_cursor.rstrip()
                buffer.insert_text("\n")

                # insert spaces to match the previous indentation level. if there's a semicolon,
                # dedent one level
                space_count: int = 0
                for char in current_line:
                    if char.isspace():
                        space_count += 1
                    else:
                        break

                buffer.insert_text(
                    " "
                    * (
                        space_count
                        # auto-dedent when it looks like a statement is completed
                        - (
                            constants.SPACES_IN_TAB
                            if current_line.strip().endswith(";")
                            else 0
                        )
                    )
                )

        @bindings.add("backspace")
        def binding_backspace(event: KeyPressEvent) -> None:
            # check if there is text currently selected that the user is trying to
            # delete by pressing backspace
            if event.current_buffer.document.selection is not None:
                buffer = event.current_buffer
                selection_start, selection_end = buffer.document.selection_range()

                buffer.exit_selection()
                buffer.document = Document(
                    buffer.document.text[:selection_start]
                    + buffer.document.text[selection_end:]
                )

                return

            # check if the preceding set of four characters is all spaces. if so,
            # this is a tab equivalent and should be removed as a group
            if (
                (
                    preceding_line_length := len(
                        event.app.current_buffer.document.current_line_before_cursor
                    )
                )
                > 0
                and preceding_line_length % 4 == 0
                and all(
                    char == " "
                    for char in event.app.current_buffer.document.current_line_before_cursor[
                        preceding_line_length
                        - (
                            constants.SPACES_IN_TAB
                            if preceding_line_length % constants.SPACES_IN_TAB == 0
                            else preceding_line_length % constants.SPACES_IN_TAB
                        ) :
                    ]
                )
            ):
                # remove the tab equivalent
                event.current_buffer.delete_before_cursor(
                    (
                        constants.SPACES_IN_TAB
                        if preceding_line_length % constants.SPACES_IN_TAB == 0
                        else preceding_line_length % constants.SPACES_IN_TAB
                    )
                )
            else:
                # otherwise, just remove an individual character like a regular backspace
                event.current_buffer.delete_before_cursor()

        @bindings.add("enter")
        def binding_enter(event: KeyPressEvent) -> None:
            # check for a blank line or a shell or sqlterm command
            if len(event.current_buffer.text.strip()) == 0 or event.current_buffer.text[
                :1
            ] in (
                constants.PREFIX_SHELL_COMMAND,
                constants.PREFIX_SQLTERM_COMMAND,
            ):
                event.current_buffer.validate_and_handle()
                return

            # check if this is a blank line and the previous line ends with ';'
            if (
                (len(event.current_buffer.document.current_line) == 0)
                and event.current_buffer.document.text.strip().endswith(";")
                or (
                    event.current_buffer.document.line_count == 1
                    and event.current_buffer.document.text.strip().endswith(";")
                    and event.current_buffer.cursor_position
                    == len(event.current_buffer.document.text)
                )
            ):
                event.current_buffer.validate_and_handle()
            else:
                insert_newline(event.current_buffer)

        @bindings.add(Keys.Escape)
        def binding_escape(event: KeyPressEvent) -> None:
            current_buffer = event.app.current_buffer
            current_buffer.cancel_completion()

            if current_buffer.complete_state is not None:
                current_buffer.complete_state.completions = []

        @bindings.add("tab")
        def binding_tab(event: KeyPressEvent) -> None:
            # map tab to four spaces
            event.app.current_buffer.insert_text(
                " "
                * (
                    constants.SPACES_IN_TAB
                    - (
                        event.app.current_buffer.document.cursor_position_col
                        % constants.SPACES_IN_TAB
                    )
                )
            )

        @bindings.add(Keys.F5)
        def binding_f5(event: KeyPressEvent) -> None:
            event.current_buffer.validate_and_handle()

        @bindings.add("c-t")
        def binding_ctrl_t(event: KeyPressEvent) -> None:
            event.current_buffer.document = Document(
                sqlparse.format(
                    event.current_buffer.document.text,
                    reindent=True,
                    indent_columns=True,
                    indent_width=4,
                    keyword_case="upper",
                    use_space_around_operators=True,
                )
            )

        @bindings.add(Keys.ControlR)
        def binding_ctrl_r(_: KeyPressEvent) -> None:
            self.parent.invalidate_completions()

        return bindings

    @property
    def _default_lexer(self: "PromptToolkitBackend") -> SqlTermLexer:
        return SqlTermLexer(parent=self)

    @property
    def _default_style(self: "PromptToolkitBackend") -> BaseStyle:
        return Style.from_dict(
            {
                "bottom-toolbar": "bg:#222222 fg:ansibrightcyan noreverse",
                "bottom-toolbar.icon": "bg:#222222 fg:ansibrightcyan noreverse",
                "bottom-toolbar.info": "fg:azure",
                "bottom-toolbar.text": "fg:darkgray",
                "error.type": "fg:ansibrightred",
                "error.message": "fg:ansibrightred",
                "prompt-cell.bracket": "fg:azure",
                "prompt-cell.number": "fg:cadetblue bold",
                "line-number": "fg:darkgray",
                "message.info": "fg:darkgray",
                "message.progress": "fg:ansibrightcyan",
                "message.sql": "fg:ansibrightcyan",
                "shell.command-sigil": "fg:darkgray",
                "shell.command": "fg:cadetblue",
            }
        )

    def display_exception(
        self: "PromptToolkitBackend", exception: Exception, unhandled: bool = False
    ) -> None:
        if not unhandled:
            print_formatted_text(
                FormattedText(
                    [
                        ("class:error.type", f"{type(exception).__name__}: "),
                        (
                            "class:error.message",
                            "\n".join(str(arg) for arg in exception.args),
                        ),
                    ]
                ),
                style=self.session.style,
            )
        else:
            print_formatted_text(
                FormattedText(
                    [
                        (
                            "class:error.message",
                            "\n".join(
                                line.strip("\n")
                                for line in traceback.format_exception(exception)
                            ),
                        )
                    ]
                ),
                style=self._default_style,
            )

    def display_info(self: "PromptToolkitBackend", info: str) -> None:
        print_formatted_text(
            FormattedText([("class:message.info", info)]),
            style=self._default_style,
        )

    def display_message_sql(self: "PromptToolkitBackend", message: str) -> None:
        print_formatted_text(
            FormattedText([("class:message.sql", message)]), style=self._default_style
        )

    def display_progress(
        self: "PromptToolkitBackend", *progress_messages: List[str]
    ) -> None:
        print_formatted_text(
            FormattedText(
                [
                    ("class:message.progress", progress_message)
                    for progress_message in progress_messages
                ]  # type: ignore
            ),
            style=self._default_style,
            end="",
        )

        # NOTE: print_formatted_text() doesn't allow '\r' as an end string so
        # we have to write it manually here
        print(end="\r")

    def _get_bottom_toolbar(self: "PromptToolkitBackend") -> List[Tuple]:
        status_details: SqlStatusDetails = self.parent.context.backends.sql.get_status()

        if status_details.connected:
            return [
                (
                    "class:bottom-toolbar.icon",
                    "\U0001f5a7 ",
                ),
                ("class:bottom-toolbar.info", status_details.connection_detail),
                ("class:bottom-toolbar.info", " "),
                ("class:bottom-toolbar.text", f"({status_details.dialect})"),
            ]
        else:
            return [
                ("class:bottom-toolbar.icon", "\u2a2f"),
                ("class:bottom-toolbar.info", " Disconnected"),
            ]

    def get_command(self: "PromptToolkitBackend") -> str:
        self.__current_statement_index += 1

        try:
            return self.session.prompt(
                [
                    ("class:prompt-cell.bracket", "["),
                    ("class:prompt-cell.number", str(self.__current_statement_index)),
                    ("class:prompt-cell.bracket", "]"),
                    ("", " " * (2 if self.__current_statement_index < 10 else 1)),
                ]
            )
        except EOFError as eof:
            raise UserExit("EOFError while prompting for input") from eof
        except KeyboardInterrupt:
            return ""

    def hide_cursor(self: "PromptToolkitBackend") -> None:
        self.session.app.output.hide_cursor()

    def _prompt_continuation(
        self, width: int, line_number: int, is_soft_wrap: bool
    ) -> List[Tuple[str, str]]:
        if (
            not is_soft_wrap
            and len(line_number_str := str(line_number + 1)) < width - 1
        ):
            return [
                (
                    "class:line-number",
                    line_number_str.rjust(width - 2) + "  ",
                )
            ]

        return [("", "...".ljust(width))]

    def prompt_for(
        self: "PromptToolkitBackend", prompt_series: Iterable[InputModel]
    ) -> List[Any]:
        return [
            self._prompt_for_input_model(input_model) for input_model in prompt_series
        ]

    def _prompt_for_input_model(
        self: "PromptToolkitBackend", input_model: InputModel
    ) -> Any:
        match input_model.type:
            case PromptType.BASIC:
                return self._prompt_for_str(
                    input_model,
                    completer=_InputModelCompleter(input_model.completer),
                    validator=_InputModelValidator(input_model.validator),
                )
            case PromptType.PASSWORD:
                return self._prompt_for_str(
                    input_model,
                    completer=_InputModelCompleter(input_model.completer),
                    validator=_InputModelValidator(input_model.validator),
                    is_password=True,
                )
            case PromptType.YES_NO:
                return self._prompt_for_yes_no(input_model)
            case _:
                raise NotImplementedError(
                    f"Prompt type {input_model.type} not implemented"
                )

    def _prompt_for_str(
        self: "PromptToolkitBackend",
        input_model: InputModel,
        validator: Validator | None = None,
        completer: Completer | None = None,
        **kwargs,
    ) -> str:
        return prompt(
            message=[("class:prompt-cell.bracket", input_model.prompt)],
            multiline=False,
            completer=completer,
            validator=validator,
            validate_while_typing=False,
            style=merge_styles(
                [
                    self.session.style,  # type: ignore
                    Style.from_dict({"": "fg:darkgray"}),
                ]
            ),
            bottom_toolbar=self.session.bottom_toolbar,
            **kwargs,
        )

    _yes_no_values: Dict[str, bool] = {"y": True, "yes": True, "n": False, "no": False}

    def _prompt_for_yes_no(
        self: "PromptToolkitBackend", input_model: InputModel
    ) -> bool:
        modified_model: InputModel = InputModel(
            input_model.prompt + " [y/n] ", input_model.type, None, None
        )

        def _yes_no_validator(user_input: str) -> str | None:
            if user_input.lower().strip() not in self._yes_no_values:
                return "Error: Please enter 'yes' or 'no'"

        return self._yes_no_values[
            self._prompt_for_str(
                modified_model, validator=_InputModelValidator(_yes_no_validator)
            )
            .lower()
            .strip()
        ]

    def refresh_structure(
        self: "PromptToolkitBackend", structure: SqlStructure
    ) -> None:
        self.__completer.refresh_structure(structure)

    @property
    def session(self: "PromptToolkitBackend") -> PromptSession:
        return self.__session

    def show_cursor(self: "PromptToolkitBackend") -> None:
        self.session.app.output.hide_cursor()
