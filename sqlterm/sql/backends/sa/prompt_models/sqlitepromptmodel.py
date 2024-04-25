import os
from typing import List

from Levenshtein import distance
from sqlalchemy import make_url
from sqlalchemy.engine import URL

from ..dataclasses import ConnectionPromptModel
from .....prompt.dataclasses import InputModel, Suggestion
from .....prompt.enums import PromptType


class SqlitePromptModel(ConnectionPromptModel):
    @staticmethod
    def construct_url(user_input: List[str]) -> URL:
        user_input[1] = user_input[1].strip()

        if len(user_input[1]) == 0:
            return make_url(user_input[0])
        else:
            return make_url("/".join(user_input))

    @staticmethod
    def path_completer(
        user_input: str, word_before_cursor: str, _: int
    ) -> List[Suggestion]:
        # get the current directory for the path the user is entering. if
        # there is no directory component, use the current directory
        user_dirname: str = os.path.dirname(user_input)
        if len(user_dirname) == 0:
            user_dirname = "."

        # if the directory the user is entering doesn't exist, return no
        # completions
        if not os.path.isdir(user_dirname):
            return []

        # build file and directory suggestions by listing the current directory
        # that the user has entered
        suggestions: List[Suggestion] = [
            Suggestion(
                filename,
                (
                    "file"
                    if os.path.isfile(os.path.join(user_dirname, filename))
                    else "dir"
                ),
                position=-len(os.path.split(user_input)[-1]),
            )
            for filename in os.listdir(user_dirname)
            if os.path.split(word_before_cursor)[-1] in filename
            or word_before_cursor.endswith(os.path.sep)
        ]

        # sort the suggestions by edit distance
        suggestions.sort(
            key=lambda suggestion: distance(suggestion.content, word_before_cursor),
        )

        return suggestions

    @staticmethod
    def path_validator(user_input: str) -> str | None:
        user_input = user_input.strip()

        # allow blank input representing the in-memory database
        if len(user_input) == 0:
            return None

        # check that the path actually exists and is a file
        if os.path.exists(user_input):
            if not os.path.isfile(user_input):
                return "Error: The provided path is not a file"
        elif user_input != ":memory:":
            return "Error: The provided file does not exist"

    _input_models: List[InputModel] = [
        InputModel(
            prompt="Database file (blank for in-memory): ",
            type=PromptType.BASIC,
            validator=path_validator,
            completer=path_completer,
        )
    ]

    def __init__(self: "SqlitePromptModel") -> None:
        super().__init__(
            input_models=self._input_models,
            url_factory=SqlitePromptModel.construct_url,
        )
