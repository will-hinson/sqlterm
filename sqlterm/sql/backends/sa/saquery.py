from sqlalchemy import text, TextClause

from ...abstract.query import Query


class SaQuery(Query):
    __sa_text: TextClause

    def __init__(self: "SaQuery", query: str) -> None:
        self.__sa_text = text(query)

    @property
    def sa_text(self: "SaQuery") -> TextClause:
        return self.__sa_text

    @property
    def text(self: "SaQuery") -> str:
        return str(self.__sa_text)
