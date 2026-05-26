"""
Roots-on-Top Event Graph Renderer
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set

@dataclass(frozen=True)
class Node:
    id: str

    @property
    def label(self) -> str:
        return self.id

@dataclass
class Graph:
    roots: List[Node] = field(default_factory=list)
    edges: Dict[Node, List[Node]] = field(default_factory=lambda: defaultdict(list))

    def add_node(self, node: Node) -> None:
        self.roots.append(node)

    def add_edge(self, parent: Node, child: Node) -> None:
        self.edges[parent].append(child)

    def children(self, node: Node) -> List[Node]:
        return self.edges.get(node, [])

    def parent(self, node: Node) -> Optional[Node]:
        for p, kids in self.edges.items():
            if node in kids:
                return p
        return None

@dataclass
class TemporalProjection:
    graph: Graph
    included_nodes: Set[Node] = field(default_factory=set)
    def get_root(self) -> Node:
        return self.graph.roots[0]

@dataclass
class ConsequenceProjection:
    graph: Graph
    included_nodes: Set[Node] = field(default_factory=set)
    def get_root(self) -> Node:
        return self.graph.roots[0]

def _build_children_map(graph: Graph) -> Dict[Node, List[Node]]:
    return dict(graph.edges)

def _compute_depth(node: Node, children_map: Dict[Node, List[Node]]) -> int:
    children = children_map.get(node, [])
    if not children:
        return 0
    return 1 + max(_compute_depth(c, children_map) for c in children)

def _assign_corridors(root: Node, children_map: Dict[Node, List[Node]]) -> Dict[Node, int]:
    corridor_of: Dict[Node, int] = {root: 0}
    next_corridor_id = 1
    queue = [root]
    while queue:
        node = queue.pop(0)
        kids = children_map.get(node, [])
        if not kids:
            continue
        heir = max(kids, key=lambda c: _compute_depth(c, children_map))
        for child in kids:
            if child == heir:
                corridor_of[child] = corridor_of[node]
            else:
                corridor_of[child] = next_corridor_id
                next_corridor_id += 1
        queue.extend(kids)
    return corridor_of

def _assign_rows_temporal(root: Node, children_map: Dict[Node, List[Node]]) -> Dict[Node, int]:
    rows: Dict[Node, int] = {}
    row_counter = 0
    def dfs(node: Node) -> None:
        nonlocal row_counter
        rows[node] = row_counter
        row_counter += 1
        for child in children_map.get(node, []):
            dfs(child)
    dfs(root)
    return rows

def _assign_rows_consequence(root: Node, children_map: Dict[Node, List[Node]]) -> Dict[Node, int]:
    rows: Dict[Node, int] = {}
    row_counter = 0
    def dfs(node: Node) -> None:
        nonlocal row_counter
        rows[node] = row_counter
        row_counter += 1
        kids = children_map.get(node, [])
        sorted_kids = sorted(kids, key=lambda c: _compute_depth(c, children_map))
        for child in sorted_kids:
            dfs(child)
    dfs(root)
    return rows

def _compute_last_row(node: Node, children_map: Dict[Node, List[Node]], rows: Dict[Node, int]) -> int:
    children = children_map.get(node, [])
    if not children:
        return rows[node]
    return max(_compute_last_row(c, children_map, rows) for c in children)

def _get_active_corridors_at_row(filtered_rows, last_rows, corridor_of, target_row):
    active = set()
    for node, r in filtered_rows.items():
        if r <= target_row <= last_rows[node]:
            active.add(corridor_of[node])
    return active

def _lane_to_col(lane: int) -> int:
    return lane * 2 + 1

def _render(projection, rows_func) -> str:
    graph = projection.graph
    root = projection.get_root()
    children_map = _build_children_map(graph)
    
    # For Consequence, we need to assign corridors based on the sorted order
    if isinstance(projection, ConsequenceProjection):
        # Re-order children in children_map based on depth
        sorted_children_map: Dict[Node, List[Node]] = {}
        def sort_recursive(node: Node):
            kids = children_map.get(node, [])
            sorted_children_map[node] = sorted(kids, key=lambda c: _compute_depth(c, children_map))
            for child in sorted_children_map[node]:
                sort_recursive(child)
        sort_recursive(root)
        corridor_of = _assign_corridors(root, sorted_children_map)
    else:
        corridor_of = _assign_corridors(root, children_map)

    rows = rows_func(root, children_map)

    active_nodes = projection.included_nodes if projection.included_nodes else set(rows.keys())
    ancestors = set()
    def add_ancestors(n: Node):
        ancestors.add(n)
        p = graph.parent(n)
        if p and p in rows:
            add_ancestors(p)
    for n in list(active_nodes):
        add_ancestors(n)
    active_nodes &= ancestors

    filtered_rows = {n: r for n, r in rows.items() if n in active_nodes}
    last_rows = {n: _compute_last_row(n, children_map, filtered_rows) for n in filtered_rows}

    if not filtered_rows:
        return ""

    max_row = max(filtered_rows.values())
    max_lane = max(corridor_of.values()) if corridor_of else 0
    num_cols = _lane_to_col(max_lane) + 1

    grid: List[List[str]] = [[' ' for _ in range(num_cols)] for _ in range(max_row + 1)]

    for node, r in filtered_rows.items():
        c = _lane_to_col(corridor_of[node])
        grid[r][c] = '○'

    for r in range(max_row + 1):
        parents_at_row = [n for n, node_r in filtered_rows.items() if node_r == r]
        for parent in parents_at_row:
            p_lane = corridor_of[parent]
            kids = children_map.get(parent, [])
            active_kids = [k for k in kids if k in filtered_rows]
            if not active_kids:
                continue
            
            heir = max(active_kids, key=lambda k: last_rows[k])
            non_heirs = [k for k in active_kids if k != heir]
            non_heirs.sort(key=lambda k: corridor_of[k])

            for kid in non_heirs:
                k_lane = corridor_of[kid]
                min_lane = min(p_lane, k_lane)
                max_lane = max(p_lane, k_lane)
                
                junction_r = r + 1
                if junction_r >= len(grid):
                    continue

                for lane in range(min_lane + 1, max_lane):
                    col = _lane_to_col(lane)
                    if 0 <= col < num_cols:
                        grid[junction_r][col] = '─'
                
                if p_lane < k_lane:
                    grid[junction_r][_lane_to_col(p_lane)] = '├'
                    grid[junction_r][_lane_to_col(k_lane)] = '╮'
                else:
                    grid[junction_r][_lane_to_col(p_lane)] = '┤'
                    grid[junction_r][_lane_to_col(k_lane)] = '╭'

    for r in range(len(grid)):
        active_corridors = _get_active_corridors_at_row(filtered_rows, last_rows, corridor_of, r)
        nodes_at_row = [n for n, node_r in filtered_rows.items() if node_r == r]
        
        for c_lane in active_corridors:
            c = _lane_to_col(c_lane)
            if any(filtered_rows[n] == r and corridor_of[n] == c_lane for n in nodes_at_row):
                continue
            if grid[r][c] == ' ':
                grid[r][c] = '│'

    lines = []
    for r in range(len(grid)):
        nodes_at_row = [(n, corridor_of[n]) for n in filtered_rows if filtered_rows[n] == r]
        label_map = {c // 2: n.label for n, c in nodes_at_row}
        
        line_chars = []
        for c in range(len(grid[0])):
            ch = grid[r][c]
            lane = c // 2
            if ch == '○' and lane in label_map:
                line_chars.append(f'○ {label_map[lane]}')
            elif ch == ' ':
                line_chars.append(' ')
            else:
                line_chars.append(ch)
        
        lines.append(''.join(line_chars).rstrip())

    return '\n'.join(lines)

def render_temporal(projection: TemporalProjection) -> str:
    return _render(projection, _assign_rows_temporal)

def render_consequence(projection: ConsequenceProjection) -> str:
    return _render(projection, _assign_rows_consequence)

def render_event_graph(projection) -> str:
    if isinstance(projection, TemporalProjection):
        return render_temporal(projection)
    elif isinstance(projection, ConsequenceProjection):
        return render_consequence(projection)
    else:
        raise ValueError(f"Unknown projection type: {type(projection)}")

def create_canonical_graph() -> Graph:
    graph = Graph()
    nodes = {name: Node(name) for name in [
        'R', 'A', 'A1', 'A2', 'A3', 'A1a', 'A1b', 'A3a', 'A3b', 'A3c'
    ]}
    graph.roots = [nodes['R']]
    graph.edges[nodes['R']] = [nodes['A']]
    graph.edges[nodes['A']] = [nodes['A1'], nodes['A2'], nodes['A3']]
    graph.edges[nodes['A1']] = [nodes['A1a']]
    graph.edges[nodes['A1a']] = [nodes['A1b']]
    graph.edges[nodes['A3']] = [nodes['A3a']]
    graph.edges[nodes['A3a']] = [nodes['A3b']]
    graph.edges[nodes['A3b']] = [nodes['A3c']]
    return graph

if __name__ == '__main__':
    nodes = {name: Node(name) for name in ['A', 'A1', 'A2', 'A3', 'A1a', 'A1b', 'A3a', 'A3b', 'A3c']}
    g = Graph()
    g.roots = [nodes['A']]
    g.edges[nodes['A']] = [nodes['A1'], nodes['A2'], nodes['A3']]
    g.edges[nodes['A1']] = [nodes['A1a']]
    g.edges[nodes['A1a']] = [nodes['A1b']]
    g.edges[nodes['A3']] = [nodes['A3a']]
    g.edges[nodes['A3a']] = [nodes['A3b']]
    g.edges[nodes['A3b']] = [nodes['A3c']]
    
    print(render_event_graph(ConsequenceProjection(g)))