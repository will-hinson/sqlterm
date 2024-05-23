"""
module sqlterm.prompt.backends.prompt_toolkit.controls.objectbrowser

Contains the definition of the ObjectBrowser class, an Application subclass that
wraps all windows/controls shown to the user when they activate the object browser
"""

from prompt_toolkit.application import Application

from ....dataclasses import SqlReference


class ObjectBrowser(Application):
    """
    class ObjectBrowser

    An Application subclass that wraps all windows/controls shown to the user
    when they activate the object browser
    """

    result: SqlReference | None

    def __init__(self, *args, **kwargs) -> None:
        self.result = None

        super().__init__(*args, **kwargs)
