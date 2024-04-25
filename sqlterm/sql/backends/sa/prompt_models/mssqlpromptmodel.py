import pyodbc
import re
import string
from typing import List

from sqlalchemy.engine import URL

from ..dataclasses import ConnectionPromptModel
from .....prompt.dataclasses import InputModel, Suggestion
from .....prompt.enums import PromptType


class MsSqlPromptModel(ConnectionPromptModel):
    _default_port: int = 1433
    _username_valid_chars: str = string.ascii_letters + string.digits + " .-_\\"

    @staticmethod
    def driver_completer(user_input: str, _: str, __: int) -> List[Suggestion]:
        return [
            Suggestion(driver_name, "driver", -len(user_input))
            for driver_name in pyodbc.drivers()
            if driver_name.startswith(user_input) or user_input in driver_name
        ]

    @staticmethod
    def driver_validator(user_input: str) -> str | None:
        user_input = user_input.strip()

        # check that the provided string is a valid driver
        if len(user_input) != 0:
            if user_input not in pyodbc.drivers():
                return "Error: ODBC driver with specified name not found"

    @staticmethod
    def host_validator(user_input: str) -> str | None:
        user_input = user_input.strip()

        # check that a blank host wasn't entered
        if len(user_input) == 0:
            return "Error: A host name must be provided"

        # this section adapted from https://stackoverflow.com/a/2532344
        if len(user_input) > 255:
            return "Error: Provided host name exceeds maximum length of 255"
        if user_input[-1] == ".":
            user_input = user_input[
                :-1
            ]  # strip exactly one dot from the right, if present
        allowed = re.compile(r"(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
        if not all(allowed.match(x) for x in user_input.split(".")):
            return "Error: Provided host name is invalid"

    @staticmethod
    def port_validator(user_input: str) -> str | None:
        user_input = user_input.strip()

        # check that the provided string is a valid port
        if len(user_input) != 0:
            try:
                int(user_input)
            except ValueError:
                return "Error: Port number must be an integer between 0 and 65535"

    @staticmethod
    def username_validator(user_input: str) -> str | None:
        user_input = user_input.strip()

        # check that a blank username wasn't entered
        if len(user_input) == 0:
            return "Error: A user name must be provided"

        # check that the username is valid
        for char in user_input:
            if char not in MsSqlPromptModel._username_valid_chars:
                return f"Error: Character '{char}' is not allowed in user name"

    @staticmethod
    def construct_url(user_input: List[str]) -> URL:
        # get everything from the user's input
        (
            dialect_schema,
            username,
            password,
            hostname,
            port,
            database,
            driver,
            trust_server_certificate,
        ) = (value.strip() if isinstance(value, str) else value for value in user_input)

        # check if there is a provided driver module (i.e., pyodbc)
        driver_name: str | None = (
            None
            if "+" not in dialect_schema
            else dialect_schema[dialect_schema.index("+") :]
        )
        if driver_name is None:
            print("No driver module specified. Defaulting to pyodbc (mssql+pyodbc)")
            dialect_schema = "mssql+pyodbc"

        # convert valid blanks to None or their defaults
        # if database == "":
        #    database = None
        if driver == "":
            driver = None
        if password == "":
            password = None
        if port == "":
            port = MsSqlPromptModel._default_port

        return URL(
            drivername=dialect_schema,
            username=username,
            password=password,
            host=hostname,
            port=int(port),
            database=database,
            query={
                "TrustServerCertificate": ("yes" if trust_server_certificate else "no"),
                **({} if driver is None else {"driver": driver}),
                **({} if password is not None else {"trusted_connection": "yes"}),
            },  # type: ignore
        )

    _input_models: List[InputModel] = [
        InputModel(
            prompt="Username: ",
            type=PromptType.BASIC,
            validator=username_validator,
        ),
        InputModel(
            prompt="Password (blank for none): ",
            type=PromptType.PASSWORD,
        ),
        InputModel(
            prompt="Host: ",
            type=PromptType.BASIC,
            validator=host_validator,
        ),
        InputModel(
            prompt="Port (blank for default): ",
            type=PromptType.BASIC,
            validator=port_validator,
        ),
        InputModel(
            prompt="Database (blank for default): ",
            type=PromptType.BASIC,
        ),
        InputModel(
            prompt="Driver (blank for default): ",
            type=PromptType.BASIC,
            completer=driver_completer,
        ),
        InputModel(
            prompt="Trust server certificate?",
            type=PromptType.YES_NO,
        ),
    ]

    def __init__(self: "MsSqlPromptModel") -> None:
        super().__init__(
            input_models=self._input_models,
            url_factory=MsSqlPromptModel.construct_url,
        )
