from ....dataclasses import SqlReference

from prompt_toolkit.application import Application


class ObjectBrowser(Application):
    result: SqlReference | None

    def __init__(self, *args, **kwargs) -> None:
        self.result = None

        super().__init__(*args, **kwargs)