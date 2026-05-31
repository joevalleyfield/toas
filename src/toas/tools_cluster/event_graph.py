"""
Roots-on-Top Event Graph Renderer
"""

from __future__ import annotations

import json
from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Node:
    id: str

    @property
    def label(self) -> str:
        return self.id


@dataclass
class Graph:
    roots: list[Node] = field(default_factory=list)
    edges: dict[Node, list[Node]] = field(default_factory=lambda: defaultdict(list))

    def add_node(self, node: Node) -> None:
        self.roots.append(node)

    def add_edge(self, parent: Node, child: Node) -> None:
        self.edges[parent].append(child)

    def children(self, node: Node) -> list[Node]:
        return self.edges.get(node, [])

    def parent(self, node: Node) -> Node | None:
        for parent, kids in self.edges.items():
            if node in kids:
                return parent
        return None


def graph_from_message_events(events: list[dict]) -> Graph:
    """Build a renderer forest from durable TOAS message events."""
    graph = Graph()
    nodes_by_id: dict[str, Node] = {}
    message_events = [
        event
        for event in events
        if isinstance(event.get("id"), str)
        and isinstance(event.get("role"), str)
        and isinstance(event.get("content"), str)
    ]

    for event in message_events:
        nodes_by_id[event["id"]] = Node(event["id"])

    for event in message_events:
        node = nodes_by_id[event["id"]]
        parent_id = event.get("parent")
        parent = nodes_by_id.get(parent_id) if isinstance(parent_id, str) else None
        if parent is None:
            graph.roots.append(node)
            continue
        graph.edges[parent].append(node)

    return graph


def graph_from_events_jsonl(path: str | Path) -> Graph:
    p = Path(path)
    if not p.exists():
        return Graph()
    with p.open(encoding="utf-8") as f:
        return graph_from_message_events([json.loads(line) for line in f if line.strip()])


@dataclass
class TemporalProjection:
    graph: Graph
    included_nodes: set[Node] = field(default_factory=set)

    def get_root(self) -> Node:
        return self.graph.roots[0]


@dataclass
class ConsequenceProjection:
    graph: Graph
    included_nodes: set[Node] = field(default_factory=set)

    def get_root(self) -> Node:
        return self.graph.roots[0]


def _build_children_map(graph: Graph) -> dict[Node, list[Node]]:
    return dict(graph.edges)


def _compute_depth(node: Node, children_map: dict[Node, list[Node]]) -> int:
    children = children_map.get(node, [])
    if not children:
        return 0
    return 1 + max(_compute_depth(child, children_map) for child in children)


def _heir(children: list[Node], children_map: dict[Node, list[Node]]) -> Node | None:
    if not children:
        return None
    return max(children, key=lambda child: _compute_depth(child, children_map))


def _assign_corridors(root: Node, children_map: dict[Node, list[Node]]) -> dict[Node, int]:
    corridor_of: dict[Node, int] = {root: 0}
    next_corridor_id = 1
    queue = deque([root])
    while queue:
        node = queue.popleft()
        kids = children_map.get(node, [])
        heir = _heir(kids, children_map)
        for child in kids:
            if child == heir:
                corridor_of[child] = corridor_of[node]
            else:
                corridor_of[child] = next_corridor_id
                next_corridor_id += 1
            queue.append(child)
    return corridor_of


def _temporal_order(root: Node, children_map: dict[Node, list[Node]]) -> list[Node]:
    """Use durable insertion order: parents expose children when their edge record appears."""
    order: list[Node] = []
    seen: set[Node] = set()

    def add(node: Node) -> None:
        if node not in seen:
            seen.add(node)
            order.append(node)

    add(root)
    for parent, kids in children_map.items():
        if parent in seen:
            for child in kids:
                add(child)
    return order


def _consequence_order(root: Node, children_map: dict[Node, list[Node]]) -> list[Node]:
    order: list[Node] = []

    def dfs(node: Node) -> None:
        order.append(node)
        kids = sorted(
            children_map.get(node, []), key=lambda child: _compute_depth(child, children_map)
        )
        for child in kids:
            dfs(child)

    dfs(root)
    return order


def _assign_rows_temporal(root: Node, children_map: dict[Node, list[Node]]) -> dict[Node, int]:
    return {node: row for row, node in enumerate(_temporal_order(root, children_map))}


def _assign_rows_consequence(root: Node, children_map: dict[Node, list[Node]]) -> dict[Node, int]:
    return {node: row for row, node in enumerate(_consequence_order(root, children_map))}


def _compute_last_row(
    node: Node, children_map: dict[Node, list[Node]], rows: dict[Node, int]
) -> int:
    children = [child for child in children_map.get(node, []) if child in rows]
    if not children:
        return rows[node]
    return max(rows[node], *(_compute_last_row(child, children_map, rows) for child in children))


def _lane_to_col(lane: int) -> int:
    return lane * 2


def _active_lanes(
    nodes: list[Node],
    rows: dict[Node, int],
    last_rows: dict[Node, int],
    lane_of: dict[Node, int],
    row: int,
) -> set[int]:
    lanes: set[int] = set()
    for node in nodes:
        if rows[node] <= row <= last_rows[node]:
            lanes.add(lane_of[node])
    return lanes


def _render_gutter(
    lanes: set[int], width: int, *, marker_lane: int | None = None, label: str | None = None
) -> str:
    chars = [" " for _ in range(width)]
    for lane in lanes:
        col = _lane_to_col(lane)
        if col < width:
            chars[col] = "│"
    if marker_lane is not None:
        marker_col = _lane_to_col(marker_lane)
        if marker_col < width:
            chars[marker_col] = "○"
        right_lanes = [lane for lane in lanes if lane > marker_lane]
        if right_lanes:
            end = _lane_to_col(max(right_lanes))
            end = min(end + 1, width - 1)
            for col in range(marker_col + 1, end + 1):
                if chars[col] == " ":
                    chars[col] = "─"
        rendered = "".join(chars).rstrip()
        return f"{rendered} {label}" if label is not None else rendered
    return "".join(chars).rstrip()


def _connector_row(parent_lane: int, child_lanes: list[int], active: set[int], width: int) -> str:
    chars = [" " for _ in range(width)]
    for lane in active:
        col = _lane_to_col(lane)
        if col < width:
            chars[col] = "│"
    for lane in sorted(set(child_lanes)):
        if lane == parent_lane:
            continue
        start = min(_lane_to_col(parent_lane), _lane_to_col(lane))
        end = max(_lane_to_col(parent_lane), _lane_to_col(lane))
        for col in range(start + 1, end):
            if chars[col] == " ":
                chars[col] = "─"
        chars[start] = "├" if parent_lane < lane else "┤"
        chars[end] = "╮" if parent_lane < lane else "╭"
    return "".join(chars).rstrip()


def _filter_rows(graph: Graph, rows: dict[Node, int], included_nodes: set[Node]) -> dict[Node, int]:
    if not included_nodes:
        return rows
    kept: set[Node] = set()

    def add_with_ancestors(node: Node) -> None:
        if node in kept or node not in rows:
            return
        kept.add(node)
        parent = graph.parent(node)
        if parent is not None:
            add_with_ancestors(parent)

    for node in included_nodes:
        add_with_ancestors(node)
    return {node: row for node, row in rows.items() if node in kept}


def _sorted_children_for_consequence(
    root: Node, children_map: dict[Node, list[Node]]
) -> dict[Node, list[Node]]:
    sorted_map: dict[Node, list[Node]] = {}

    def visit(node: Node) -> None:
        kids = sorted(
            children_map.get(node, []), key=lambda child: _compute_depth(child, children_map)
        )
        sorted_map[node] = kids
        for child in kids:
            visit(child)

    visit(root)
    return sorted_map


def _nodes_by_row(rows: dict[Node, int]) -> list[Node]:
    return sorted(rows, key=lambda node: rows[node])


def _render_temporal_root(projection: TemporalProjection, root: Node) -> str:
    graph = projection.graph
    children_map = _build_children_map(graph)
    rows = _filter_rows(graph, _assign_rows_temporal(root, children_map), projection.included_nodes)
    if not rows:
        return ""
    nodes = _nodes_by_row(rows)
    lane_of = _assign_corridors(root, children_map)
    last_rows = {node: _compute_last_row(node, children_map, rows) for node in nodes}
    width = _lane_to_col(max(lane_of[node] for node in nodes)) + 1

    lines: list[str] = []
    for index, node in enumerate(nodes):
        row = rows[node]
        parent = graph.parent(node)
        if parent in rows and lane_of[parent] != lane_of[node]:
            connector_active = _active_lanes(nodes, rows, last_rows, lane_of, row)
            lines.append(_connector_row(lane_of[parent], [lane_of[node]], connector_active, width))
        active = _active_lanes(nodes, rows, last_rows, lane_of, row)
        lines.append(_render_gutter(active, width, marker_lane=lane_of[node], label=node.label))
        if index + 1 < len(nodes):
            next_node = nodes[index + 1]
            next_parent = graph.parent(next_node)
            next_has_connector = next_parent in rows and lane_of[next_parent] != lane_of[next_node]
            if (lane_of[next_node] == lane_of[node] and next_parent == node) or (
                lane_of[next_node] != lane_of[node] and not next_has_connector
            ):
                lines.append(
                    _render_gutter(_active_lanes(nodes, rows, last_rows, lane_of, row + 1), width)
                )
    return "\n".join(line for line in lines if line)


def _assign_consequence_lanes(
    root: Node, children_map: dict[Node, list[Node]], order: list[Node]
) -> dict[Node, int]:
    lane_of = {root: 0}
    for node in order:
        kids = children_map.get(node, [])
        heir = _heir(kids, children_map)
        for child in kids:
            lane_of[child] = lane_of[node] if child == heir else 1
    return lane_of


def _render_consequence_root(projection: ConsequenceProjection, root: Node) -> str:
    graph = projection.graph
    raw_children_map = _build_children_map(graph)
    children_map = _sorted_children_for_consequence(root, raw_children_map)
    rows = _filter_rows(
        graph, _assign_rows_consequence(root, raw_children_map), projection.included_nodes
    )
    if not rows:
        return ""
    nodes = _nodes_by_row(rows)
    lane_of = _assign_consequence_lanes(root, children_map, nodes)
    last_rows = {node: _compute_last_row(node, children_map, rows) for node in nodes}
    width = _lane_to_col(max(lane_of[node] for node in nodes)) + 1

    lines: list[str] = []
    for index, node in enumerate(nodes):
        row = rows[node]
        parent = graph.parent(node)
        if parent in rows and lane_of[parent] != lane_of[node]:
            connector_active = _active_lanes(nodes, rows, last_rows, lane_of, row)
            lines.append(_connector_row(lane_of[parent], [lane_of[node]], connector_active, width))
        active = _active_lanes(nodes, rows, last_rows, lane_of, row)
        lines.append(_render_gutter(active, width, marker_lane=lane_of[node], label=node.label))
        if index + 1 < len(nodes):
            next_node = nodes[index + 1]
            if (lane_of[next_node] == lane_of[node] and graph.parent(next_node) == node) or (
                lane_of[next_node] < lane_of[node] and rows[next_node] <= last_rows[root]
            ):
                lines.append(
                    _render_gutter(_active_lanes(nodes, rows, last_rows, lane_of, row + 1), width)
                )
    return "\n".join(line for line in lines if line)


def render_temporal(projection: TemporalProjection) -> str:
    return "\n\n".join(
        rendered
        for root in projection.graph.roots
        if (rendered := _render_temporal_root(projection, root))
    )


def render_consequence(projection: ConsequenceProjection) -> str:
    return "\n\n".join(
        rendered
        for root in projection.graph.roots
        if (rendered := _render_consequence_root(projection, root))
    )


def render_event_graph(projection) -> str:
    if isinstance(projection, TemporalProjection):
        return render_temporal(projection)
    if isinstance(projection, ConsequenceProjection):
        return render_consequence(projection)
    raise ValueError(f"Unknown projection type: {type(projection)}")


def create_canonical_graph() -> Graph:
    graph = Graph()
    nodes = {
        name: Node(name) for name in ["R", "A", "A1", "A2", "A3", "A1a", "A1b", "A3a", "A3b", "A3c"]
    }
    graph.roots = [nodes["R"]]
    graph.edges[nodes["R"]] = [nodes["A"]]
    graph.edges[nodes["A"]] = [nodes["A1"], nodes["A2"], nodes["A3"]]
    graph.edges[nodes["A1"]] = [nodes["A1a"]]
    graph.edges[nodes["A1a"]] = [nodes["A1b"]]
    graph.edges[nodes["A3"]] = [nodes["A3a"]]
    graph.edges[nodes["A3a"]] = [nodes["A3b"]]
    graph.edges[nodes["A3b"]] = [nodes["A3c"]]
    return graph
