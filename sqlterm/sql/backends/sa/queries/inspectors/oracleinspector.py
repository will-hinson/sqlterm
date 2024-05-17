from .sqlinspector import SqlInspector


class OracleInspector(SqlInspector):
    def refresh_structure(self: "OracleInspector") -> None:
        raise Exception("TODO: Oracle SQL inspection")
