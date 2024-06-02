from dataclasses import dataclass
from enum import StrEnum
from threading import Thread
import time
from typing import Dict, List, Tuple
from xml.etree import ElementTree

from sqlalchemy import Connection
from tqdm import tqdm

from .sqlprofiler import SqlProfiler


class _MsSqlProfilerQuery(StrEnum):
    NODE_STATUS = """
    SELECT
        c.[node_id],
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
    progress_bar: tqdm | None = None


@dataclass
class _NodeStatus:
    node_id: int
    row_count: int
    estimate_row_count: int
    first_active_time: int
    last_active_time: int


class MsSqlProfiler(SqlProfiler):
    __session_id: int

    def __init__(self: "MsSqlProfiler", parent) -> None:
        super().__init__(parent)

        self.__session_id = self.parent.connection.execute(
            self.parent.make_query(_MsSqlProfilerQuery.SESSION_ID).sa_text
        ).fetchone()[  # type: ignore
            0
        ]

    def _create_progress_bars(
        self: "MsSqlProfiler",
        operator_tree: List[_OperatorNode],
        depth: int = 0,
        start_position: int = 0,
    ) -> int:
        for operator in operator_tree:
            operator.progress_bar = tqdm(
                leave=True,
                position=start_position,
                desc=("  " * depth) + operator.element.attrib["LogicalOp"],
                unit="rows",
                unit_scale=True,
            )
            start_position += 1
            start_position = self._create_progress_bars(
                operator.children, depth=depth + 1, start_position=start_position
            )

        return start_position

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

        # get all of the operators as a tree structure and a flattened dict
        operator_tree: List[_OperatorNode] = []
        for rel_op in query_plan.findall(
            "{http://schemas.microsoft.com/sqlserver/2004/07/showplan}RelOp"
        ):
            operator_tree.append(
                _OperatorNode(
                    rel_op,
                    node_id=int(rel_op.attrib["NodeId"]),
                    children=self._get_children_operators(rel_op),
                )
            )
        operator_dict: Dict[int, _OperatorNode] = self._operator_tree_to_dict(
            operator_tree
        )

        # populate progress bars for all of the operators
        self._create_progress_bars(operator_tree)

        # loop while we're able to get status records
        records_fetched: int = -1
        while records_fetched != 0:
            records_fetched = 0
            for node_status in (
                _NodeStatus(*record)
                for record in connection.execute(
                    self.parent.make_query(
                        _MsSqlProfilerQuery.NODE_STATUS.replace(
                            "?", str(self.__session_id).replace("'", "''")
                        )
                    ).sa_text
                ).fetchall()
            ):
                node_progress_bar: tqdm = operator_dict[
                    node_status.node_id
                ].progress_bar  # type: ignore
                node_progress_bar.total = max(
                    node_status.estimate_row_count, node_status.row_count
                )
                node_progress_bar.update(node_status.row_count - node_progress_bar.n)

                records_fetched += 1

            time.sleep(0.25)

        # close all progress bars
        for operator_node in operator_dict.values():
            if operator_node.progress_bar is not None:
                operator_node.progress_bar.close()

    def _operator_tree_to_dict(
        self: "MsSqlProfiler", operator_tree: List[_OperatorNode]
    ) -> Dict[int, _OperatorNode]:
        operator_dict: Dict[int, _OperatorNode] = {}
        for operator_node in operator_tree:
            operator_dict[operator_node.node_id] = operator_node
            operator_dict.update(self._operator_tree_to_dict(operator_node.children))

        return operator_dict

    def profile_query(self: "MsSqlProfiler") -> None:
        self.current_thread = Thread(target=self._run)
        self.current_thread.daemon = True

        self.current_thread.run()
