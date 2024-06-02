from dataclasses import dataclass
from enum import StrEnum
from threading import Thread
from typing import List, Tuple
from xml.etree import ElementTree

from sqlalchemy import Connection

from ..managers import QueryManager
from .sqlprofiler import SqlProfiler


class _MsSqlProfilerQuery(StrEnum):
    NODE_STATUS = """
    SELECT
        c.[node_id],
        c.[physical_operator_name],
        c.[row_count],
        c.[estimate_row_count],
        first_active_time = NULLIF(c.[first_active_time], 0),
        last_active_time = NULLIF(c.[last_active_time], 0)
    FROM (
        SELECT TOP 1
            *
        FROM
            sys.dm_exec_requests
        WHERE
            [session_id] = '?'
    ) AS a
    INNER JOIN sys.dm_exec_query_stats AS b ON
        a.[sql_handle] = b.[sql_handle]
    INNER JOIN sys.dm_exec_query_profiles AS c ON
        a.[sql_handle] = c.[sql_handle];
    """
    QUERY_PLAN_XML = """
    SELECT TOP 1
        [query_plan]
    FROM
        sys.dm_exec_query_plan(
            (
                SELECT TOP 1
                    [plan_handle]
                FROM
                    sys.dm_exec_requests
                WHERE
                    [session_id] = '?'
            )
        );
    """
    SESSION_ID = "SELECT @@SPID;"


@dataclass
class _OperatorNode:
    element: ElementTree.Element
    node_id: int
    children: List["_OperatorNode"]


class MsSqlProfiler(SqlProfiler):
    __session_id: int

    def __init__(self: "MsSqlProfiler", parent) -> None:
        super().__init__(parent)

        self.__session_id = self.parent.connection.execute(
            self.parent.make_query(_MsSqlProfilerQuery.SESSION_ID).sa_text
        ).fetchone()[  # type: ignore
            0
        ]

    def _get_children_operators(
        self: "MsSqlProfiler", root_element: ElementTree.Element
    ) -> List[_OperatorNode]:
        # try to find the actual element in the tree that will contain the
        # operators that feed into this one
        target_element: ElementTree.Element | None = None
        for current_element in root_element.findall("./*"):
            if current_element.tag.rpartition("}")[-1] not in (
                "DefinedValues",
                "OutputList",
                "Warnings",
            ):
                target_element = current_element
                break

        if target_element is None:
            return []

        # get all of the child operators of this one
        output_rel_ops: List[_OperatorNode] = []
        for rel_op in target_element.findall(
            "{http://schemas.microsoft.com/sqlserver/2004/07/showplan}RelOp"
        ):
            output_rel_ops.append(
                _OperatorNode(
                    rel_op,
                    node_id=int(rel_op.attrib["NodeId"]),
                    children=self._get_children_operators(rel_op),
                )
            )

        return output_rel_ops

    def _run(self: "MsSqlProfiler") -> None:
        connection: Connection = self.parent.make_connection()

        # try to get the query plan for the current query
        show_plan_result: Tuple | None = connection.execute(
            self.parent.make_query(
                _MsSqlProfilerQuery.QUERY_PLAN_XML.replace(
                    "?", str(self.__session_id).replace("'", "''")
                )
            ).sa_text
        ).fetchone()  # type: ignore

        # if we didn't get a plan, the query was faster than us. give up
        if show_plan_result is None:
            return

        # otherwise, parse out the first available query plan
        show_plan_xml: ElementTree.Element = ElementTree.fromstring(show_plan_result[0])
        query_plan: ElementTree.Element | None = None
        for current_element in show_plan_xml.iter():
            if current_element.tag.endswith("}QueryPlan"):
                query_plan = current_element
                break

        # if we didn't find a query plan, give up
        if query_plan is None:
            return None

        # get all of the operators as a tree structure
        output_rel_ops: List[_OperatorNode] = []
        for rel_op in query_plan.findall(
            "{http://schemas.microsoft.com/sqlserver/2004/07/showplan}RelOp"
        ):
            output_rel_ops.append(
                _OperatorNode(
                    rel_op,
                    node_id=int(rel_op.attrib["NodeId"]),
                    children=self._get_children_operators(rel_op),
                )
            )

        print(output_rel_ops)

    def profile_query(self: "MsSqlProfiler") -> None:
        self.current_thread = Thread(target=self._run)
        self.current_thread.daemon = True

        self.current_thread.run()
