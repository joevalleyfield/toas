"""
Roots-on-Top Event Graph Renderer
"""

from __future__ import annotations

import json
from bisect import bisect_right
from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Node:
    id: str
    label_text: str | None = None

    @property
    def label(self) -> str:
        return self.label_text or self.id


@dataclass
class Graph:
    roots: list[Node] = field(default_factory=list)
    edges: dict[Node, list[Node]] = field(default_factory=lambda: defaultdict(list))
    ordered_nodes: list[Node] = field(default_factory=list)
    parent_of: dict[Node, Node] = field(default_factory=dict)

    def add_node(self, node: Node) -> None:
        self.roots.append(node)

    def add_edge(self, parent: Node, child: Node) -> None:
        self.edges[parent].append(child)
        self.parent_of[child] = parent

    def children(self, node: Node) -> list[Node]:
        return self.edges.get(node, [])

    def parent(self, node: Node) -> Node | None:
        return self.parent_of.get(node)


def graph_from_message_events(events: list[dict]) -> Graph:
    """Build a renderer forest from durable TOAS message events."""
    graph = Graph()
    nodes_by_id: dict[str, Node] = {}
    message_events: list[dict] = []
    seen_ids: set[str] = set()
    for event in events:
        event_id = event.get("id")
        if (
            not isinstance(event_id, str)
            or not isinstance(event.get("role"), str)
            or not isinstance(event.get("content"), str)
            or event_id in seen_ids
        ):
            continue
        seen_ids.add(event_id)
        message_events.append(event)

    for event in message_events:
        nodes_by_id[event["id"]] = Node(event["id"], _event_label(event))
        graph.ordered_nodes.append(nodes_by_id[event["id"]])

    for event in message_events:
        node = nodes_by_id[event["id"]]
        parent_id = event.get("parent")
        parent = nodes_by_id.get(parent_id) if isinstance(parent_id, str) else None
        if parent is None:
            graph.roots.append(node)
            continue
        graph.edges[parent].append(node)
        graph.parent_of[node] = parent

    return graph


def _event_label(event: dict) -> str:
    message_id = str(event["id"])
    role = str(event["role"]).strip().lower()
    role_char = role[:1] or "?"
    content_lines = str(event["content"]).splitlines()
    first_line = content_lines[0].strip() if content_lines else ""
    label = f"{message_id} {role_char}"
    if first_line:
        label = f"{label} {first_line}"
    if len(label) <= 66:
        return label
    return label[:63] + "..."


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


def _compute_depth(
    node: Node, children_map: dict[Node, list[Node]], memo: dict[Node, int] | None = None
) -> int:
    if memo is not None and node in memo:
        return memo[node]
    children = children_map.get(node, [])
    if not children:
        depth = 0
    else:
        depth = 1 + max(_compute_depth(child, children_map, memo) for child in children)
    if memo is not None:
        memo[node] = depth
    return depth


def _compute_depths(children_map: dict[Node, list[Node]]) -> dict[Node, int]:
    nodes: set[Node] = set(children_map)
    for children in children_map.values():
        nodes.update(children)
    depths = dict.fromkeys(nodes, 0)
    remaining_children = {node: len(children_map.get(node, [])) for node in nodes}
    parents_by_child: dict[Node, list[Node]] = defaultdict(list)
    queue: deque[Node] = deque()
    for parent, children in children_map.items():
        for child in children:
            parents_by_child[child].append(parent)
    for node, child_count in remaining_children.items():
        if child_count == 0:
            queue.append(node)
    while queue:
        node = queue.popleft()
        for parent in parents_by_child.get(node, []):
            depths[parent] = max(depths[parent], depths[node] + 1)
            remaining_children[parent] -= 1
            if remaining_children[parent] == 0:
                queue.append(parent)
    return depths


def _heir(
    children: list[Node], children_map: dict[Node, list[Node]], depth_memo: dict[Node, int] | None = None
) -> Node | None:
    if not children:
        return None
    if depth_memo is not None:
        return max(children, key=lambda child: depth_memo.get(child, 0))
    return max(children, key=lambda child: _compute_depth(child, children_map, depth_memo))


def _assign_corridors(root: Node, children_map: dict[Node, list[Node]]) -> dict[Node, int]:
    corridor_of: dict[Node, int] = {root: 0}
    next_corridor_id = 1
    queue = deque([root])
    depth_memo = _compute_depths(children_map)
    visited: set[Node] = set()
    while queue:
        node = queue.popleft()
        if node in visited:
            continue
        visited.add(node)
        kids = children_map.get(node, [])
        heir = _heir(kids, children_map, depth_memo)
        for child in kids:
            if child == heir:
                corridor_of[child] = corridor_of[node]
            else:
                corridor_of[child] = next_corridor_id
                next_corridor_id += 1
            queue.append(child)
    return corridor_of


def _temporal_order(graph: Graph, root: Node, children_map: dict[Node, list[Node]]) -> list[Node]:
    """Preserve durable message-event order within a root's lineage."""
    if graph.ordered_nodes:
        descendants = _descendants(root, children_map)
        return [node for node in graph.ordered_nodes if node in descendants]

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


def _descendants(root: Node, children_map: dict[Node, list[Node]]) -> set[Node]:
    descendants: set[Node] = set()
    stack = [root]
    while stack:
        node = stack.pop()
        if node in descendants:
            continue
        descendants.add(node)
        stack.extend(children_map.get(node, []))
    return descendants


def _consequence_order(root: Node, children_map: dict[Node, list[Node]]) -> list[Node]:
    order: list[Node] = []
    depth_memo = _compute_depths(children_map)
    stack = [root]
    while stack:
        node = stack.pop()
        order.append(node)
        kids = sorted(
            children_map.get(node, []), key=lambda child: depth_memo.get(child, 0)
        )
        stack.extend(reversed(kids))
    return order


def _assign_rows_temporal(
    graph: Graph, root: Node, children_map: dict[Node, list[Node]]
) -> dict[Node, int]:
    return {node: row for row, node in enumerate(_temporal_order(graph, root, children_map))}


def _assign_rows_consequence(root: Node, children_map: dict[Node, list[Node]]) -> dict[Node, int]:
    return {node: row for row, node in enumerate(_consequence_order(root, children_map))}


def _compute_last_rows(
    nodes: list[Node],
    children_map: dict[Node, list[Node]],
    rows: dict[Node, int],
    lane_of: dict[Node, int],
) -> dict[Node, int]:
    last_rows = {node: rows[node] for node in nodes}
    for node in reversed(nodes):
        children = [child for child in children_map.get(node, []) if child in rows]
        same_lane_children = [child for child in children if lane_of.get(child) == lane_of.get(node)]
        relevant_children = same_lane_children or children
        if relevant_children:
            last_rows[node] = max(rows[node], *(last_rows[child] for child in relevant_children))
    return last_rows


def _lane_to_col(lane: int) -> int:
    return lane * 2


def _active_lanes(
    active_lanes_by_row: dict[int, set[int]],
    row: int,
) -> set[int]:
    return active_lanes_by_row.get(row, set())


def _active_lanes_by_row(
    nodes: list[Node],
    start_rows: dict[Node, int],
    last_rows: dict[Node, int],
    lane_of: dict[Node, int],
) -> dict[int, set[int]]:
    if not nodes:
        return {}
    starts: dict[int, list[int]] = defaultdict(list)
    ends: dict[int, list[int]] = defaultdict(list)
    for node in nodes:
        lane = lane_of[node]
        starts[start_rows[node]].append(lane)
        ends[last_rows[node] + 1].append(lane)
    active_counts: dict[int, int] = defaultdict(int)
    active_by_row: dict[int, set[int]] = {}
    for row in range(min(start_rows.values()), max(last_rows.values()) + 1):
        for lane in starts.get(row, []):
            active_counts[lane] += 1
        for lane in ends.get(row, []):
            active_counts[lane] -= 1
            if active_counts[lane] <= 0:
                del active_counts[lane]
        active_by_row[row] = set(active_counts)
    return active_by_row


def _compute_start_rows(
    graph: Graph, nodes: list[Node], rows: dict[Node, int], lane_of: dict[Node, int]
) -> dict[Node, int]:
    start_rows: dict[Node, int] = {}
    rows_by_lane: dict[int, list[int]] = defaultdict(list)
    for node in nodes:
        rows_by_lane[lane_of[node]].append(rows[node])
    for lane_rows in rows_by_lane.values():
        lane_rows.sort()
    for node in nodes:
        parent = graph.parent(node)
        if parent is not None and parent in rows and lane_of.get(parent) != lane_of.get(node):
            parent_lane = lane_of[parent]
            parent_row = rows[parent]
            parent_lane_rows = rows_by_lane[parent_lane]
            next_index = bisect_right(parent_lane_rows, parent_row)
            first_parent_lane_continuation = (
                parent_lane_rows[next_index] if next_index < len(parent_lane_rows) else rows[node]
            )
            start_rows[node] = min(rows[node], first_parent_lane_continuation)
        else:
            start_rows[node] = rows[node]
    return start_rows


def _pending_branch_lanes(
    graph: Graph,
    rows: dict[Node, int],
    start_rows: dict[Node, int],
    lane_of: dict[Node, int],
    parent: Node,
    children_map: dict[Node, list[Node]],
) -> list[int]:
    parent_row = rows[parent]
    lanes: list[int] = []
    for node in children_map.get(parent, []):
        if node not in rows:
            continue
        if lane_of.get(node) == lane_of.get(parent):
            continue
        if start_rows[node] == parent_row + 1 and rows[node] > start_rows[node]:
            lanes.append(lane_of[node])
    return sorted(set(lanes))


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
    depth_memo = _compute_depths(children_map)
    stack = [root]
    while stack:
        node = stack.pop()
        kids = sorted(
            children_map.get(node, []), key=lambda child: depth_memo.get(child, 0)
        )
        sorted_map[node] = kids
        stack.extend(reversed(kids))
    return sorted_map


def _nodes_by_row(rows: dict[Node, int]) -> list[Node]:
    return sorted(rows, key=lambda node: rows[node])


def _render_temporal_root(projection: TemporalProjection, root: Node) -> str:
    graph = projection.graph
    children_map = _build_children_map(graph)
    rows = _filter_rows(
        graph, _assign_rows_temporal(graph, root, children_map), projection.included_nodes
    )
    if not rows:
        return ""
    nodes = _nodes_by_row(rows)
    lane_of = _assign_corridors(root, children_map)
    last_rows = _compute_last_rows(nodes, children_map, rows, lane_of)
    start_rows = _compute_start_rows(graph, nodes, rows, lane_of)
    active_by_row = _active_lanes_by_row(nodes, start_rows, last_rows, lane_of)
    width = _lane_to_col(max(lane_of[node] for node in nodes)) + 1

    lines: list[str] = []
    for index, node in enumerate(nodes):
        row = rows[node]
        parent = graph.parent(node)
        if parent in rows and lane_of[parent] != lane_of[node] and rows[node] == start_rows[node]:
            connector_active = _active_lanes(active_by_row, row)
            lines.append(_connector_row(lane_of[parent], [lane_of[node]], connector_active, width))
        active = _active_lanes(active_by_row, row)
        lines.append(_render_gutter(active, width, marker_lane=lane_of[node], label=node.label))
        pending_lanes = _pending_branch_lanes(graph, rows, start_rows, lane_of, node, children_map)
        if pending_lanes:
            connector_active = _active_lanes(active_by_row, row + 1)
            lines.append(_connector_row(lane_of[node], pending_lanes, connector_active, width))
            continue
        if index + 1 < len(nodes):
            next_node = nodes[index + 1]
            next_parent = graph.parent(next_node)
            next_has_connector = (
                next_parent in rows
                and lane_of[next_parent] != lane_of[next_node]
                and rows[next_node] == start_rows[next_node]
            )
            if (lane_of[next_node] == lane_of[node] and next_parent == node) or (
                lane_of[next_node] != lane_of[node] and not next_has_connector
            ):
                lines.append(
                    _render_gutter(
                        _active_lanes(active_by_row, row + 1), width
                    )
                )
    return "\n".join(line for line in lines if line)


def _assign_consequence_lanes(
    root: Node, children_map: dict[Node, list[Node]], order: list[Node]
) -> dict[Node, int]:
    lane_of = {root: 0}
    depth_memo = _compute_depths(children_map)
    for node in order:
        kids = children_map.get(node, [])
        heir = _heir(kids, children_map, depth_memo)
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
    last_rows = _compute_last_rows(nodes, children_map, rows, lane_of)
    start_rows = _compute_start_rows(graph, nodes, rows, lane_of)
    active_by_row = _active_lanes_by_row(nodes, start_rows, last_rows, lane_of)
    width = _lane_to_col(max(lane_of[node] for node in nodes)) + 1

    lines: list[str] = []
    for index, node in enumerate(nodes):
        row = rows[node]
        parent = graph.parent(node)
        if parent in rows and lane_of[parent] != lane_of[node]:
            connector_active = _active_lanes(active_by_row, row)
            lines.append(_connector_row(lane_of[parent], [lane_of[node]], connector_active, width))
        active = _active_lanes(active_by_row, row)
        lines.append(_render_gutter(active, width, marker_lane=lane_of[node], label=node.label))
        if index + 1 < len(nodes):
            next_node = nodes[index + 1]
            if (lane_of[next_node] == lane_of[node] and graph.parent(next_node) == node) or (
                lane_of[next_node] < lane_of[node] and rows[next_node] <= last_rows[root]
            ):
                lines.append(
                    _render_gutter(
                        _active_lanes(active_by_row, row + 1), width
                    )
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
    graph.parent_of = {
        child: parent for parent, children in graph.edges.items() for child in children
    }
    return graph
