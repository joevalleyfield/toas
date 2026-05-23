#!/usr/bin/env python3
"""Canonical prefix collapse for TOAS legacy message graphs.

This script is read-only by default. It builds a canonicalized DAG by walking
legacy message nodes in append order and folding nodes by the tuple:
    (canonical_parent, role, content)

That root-up process reconstructs shared prefixes even when raw parent ids differ
before collapse (e.g. n5->n0 then n6->n2 once parent canonicalizes).

Outputs:
- graph cardinality before/after
- mapping samples
- raw vs canonical path lengths to a target id
- transcript byte/line sizes for raw and canonical path projections
"""

from __future__ import annotations

import argparse
import json
import re
from difflib import SequenceMatcher
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class LegacyNode:
    id: str
    parent: Optional[str]
    role: str
    content: str
    line_no: int


@dataclass(frozen=True)
class CanonNode:
    id: str
    parent: Optional[str]
    role: str
    content: str


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Canonical prefix collapse for TOAS legacy message graphs")
    ap.add_argument("events", type=Path, help="Path to events.jsonl")
    ap.add_argument("--target", default="n15218", help="Target legacy message id")
    ap.add_argument("--show-mapping", type=int, default=30, help="How many remapped pairs to print")
    ap.add_argument(
        "--normalize",
        choices=("none", "whitespace"),
        default="none",
        help="Normalization mode for content equality",
    )
    ap.add_argument(
        "--near-root-threshold",
        type=float,
        default=0.985,
        help="Similarity threshold (0..1) for near-root diagnostics against n0",
    )
    ap.add_argument(
        "--near-root-limit",
        type=int,
        default=30,
        help="Max number of near-root anomalies to print",
    )
    return ap.parse_args()


_HEADING_RE = re.compile(r"^(#{1,6})\s*(.*?)\s*$", re.MULTILINE)


def normalize_whitespace_structural(text: str) -> str:
    """Canonicalize whitespace without dropping semantic tokens.

    Rules:
    - normalize CRLF/CR to LF
    - trim trailing spaces per line
    - normalize heading spacing (`##Heading` -> `## Heading`)
    - ensure blank line before/after Markdown headings (except file boundaries)
    - collapse 3+ consecutive blank lines to exactly 2
    """

    t = text.replace("\r\n", "\n").replace("\r", "\n")
    t = "\n".join(line.rstrip() for line in t.split("\n"))

    def _heading_fix(m: re.Match[str]) -> str:
        hashes = m.group(1)
        body = m.group(2).strip()
        return f"{hashes} {body}" if body else hashes

    t = _HEADING_RE.sub(_heading_fix, t)

    lines = t.split("\n")
    out: list[str] = []
    n = len(lines)
    for i, line in enumerate(lines):
        is_heading = bool(re.match(r"^#{1,6}\s", line))
        if is_heading and out and out[-1] != "":
            out.append("")
        out.append(line)
        if is_heading:
            nxt = lines[i + 1] if i + 1 < n else None
            if nxt is not None and nxt != "":
                out.append("")

    t = "\n".join(out)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip("\n")


def load_legacy_messages(events_path: Path) -> List[LegacyNode]:
    out: List[LegacyNode] = []
    with events_path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if "kind" in row:
                continue
            mid = row.get("id")
            if not (isinstance(mid, str) and mid.startswith("n")):
                continue
            out.append(
                LegacyNode(
                    id=mid,
                    parent=row.get("parent"),
                    role=row.get("role", ""),
                    content=row.get("content", ""),
                    line_no=line_no,
                )
            )
    return out


def collapse_prefix(nodes: List[LegacyNode], *, normalize_mode: str = "none") -> Tuple[Dict[str, str], Dict[str, CanonNode]]:
    """Return (legacy->canonical id map, canonical node dict)."""
    legacy_to_canon: Dict[str, str] = {}
    key_to_canon: Dict[Tuple[Optional[str], str, str], str] = {}
    canon_nodes: Dict[str, CanonNode] = {}
    next_idx = 0

    for n in nodes:
        canon_parent = legacy_to_canon.get(n.parent) if isinstance(n.parent, str) else None
        content_key = n.content
        if normalize_mode == "whitespace":
            content_key = normalize_whitespace_structural(content_key)
        key = (canon_parent, n.role, content_key)
        existing = key_to_canon.get(key)
        if existing is not None:
            legacy_to_canon[n.id] = existing
            continue

        cid = f"c{next_idx}"
        next_idx += 1
        key_to_canon[key] = cid
        legacy_to_canon[n.id] = cid
        canon_nodes[cid] = CanonNode(id=cid, parent=canon_parent, role=n.role, content=n.content)

    return legacy_to_canon, canon_nodes


def lineage_legacy(id_to_node: Dict[str, LegacyNode], target: str) -> List[str]:
    if target not in id_to_node:
        raise KeyError(f"target not found: {target}")
    out: List[str] = []
    cur: Optional[str] = target
    seen = set()
    while cur is not None and cur in id_to_node:
        if cur in seen:
            raise RuntimeError(f"cycle detected in legacy lineage at {cur}")
        seen.add(cur)
        out.append(cur)
        p = id_to_node[cur].parent
        cur = p if isinstance(p, str) else None
    out.reverse()
    return out


def lineage_canon(canon_nodes: Dict[str, CanonNode], target_canon: str) -> List[str]:
    if target_canon not in canon_nodes:
        raise KeyError(f"canonical target not found: {target_canon}")
    out: List[str] = []
    cur: Optional[str] = target_canon
    seen = set()
    while cur is not None and cur in canon_nodes:
        if cur in seen:
            raise RuntimeError(f"cycle detected in canonical lineage at {cur}")
        seen.add(cur)
        out.append(cur)
        cur = canon_nodes[cur].parent
    out.reverse()
    return out


def render_transcript_from_legacy(ids: List[str], id_to_node: Dict[str, LegacyNode]) -> str:
    # Match current transcript projection style for legacy records.
    parts: List[str] = []
    for mid in ids:
        n = id_to_node[mid]
        role = n.role.upper() if n.role else "UNKNOWN"
        parts.append(f"## TOAS:{role}\n\n{n.content}")
    return "\n\n".join(parts)


def render_transcript_from_canon(ids: List[str], canon_nodes: Dict[str, CanonNode]) -> str:
    parts: List[str] = []
    for cid in ids:
        n = canon_nodes[cid]
        role = n.role.upper() if n.role else "UNKNOWN"
        parts.append(f"## TOAS:{role}\n\n{n.content}")
    return "\n\n".join(parts)


def main() -> int:
    args = parse_args()
    nodes = load_legacy_messages(args.events)
    if not nodes:
        print("no legacy message nodes found")
        return 1

    id_to_node = {n.id: n for n in nodes}
    roots = [n.id for n in nodes if not (isinstance(n.parent, str) and n.parent in id_to_node)]

    legacy_to_canon, canon_nodes = collapse_prefix(nodes, normalize_mode=args.normalize)

    raw_lineage = lineage_legacy(id_to_node, args.target)
    target_canon = legacy_to_canon[args.target]
    canon_lineage = lineage_canon(canon_nodes, target_canon)

    raw_transcript = render_transcript_from_legacy(raw_lineage, id_to_node)
    canon_transcript = render_transcript_from_canon(canon_lineage, canon_nodes)

    print(f"events={args.events}")
    print(f"normalize_mode={args.normalize}")
    print(f"roots={len(roots)} sample={roots[:5]}")
    print(f"legacy_nodes={len(nodes)} canonical_nodes={len(canon_nodes)}")
    print(f"target={args.target} -> canonical_target={target_canon}")
    print(f"raw_lineage_nodes={len(raw_lineage)} canonical_lineage_nodes={len(canon_lineage)}")
    print(f"raw_transcript_bytes={len(raw_transcript.encode('utf-8'))} lines={raw_transcript.count(chr(10))+1}")
    print(f"canon_transcript_bytes={len(canon_transcript.encode('utf-8'))} lines={canon_transcript.count(chr(10))+1}")

    remapped = [(lid, cid) for lid, cid in legacy_to_canon.items() if lid != cid]
    remapped.sort(key=lambda t: int(t[0][1:]) if t[0][1:].isdigit() else 10**12)
    print(f"remapped_count={len(remapped)}")
    if remapped:
        print("remapped_sample:")
        for lid, cid in remapped[: max(0, args.show_mapping)]:
            print(f"  {lid} -> {cid}")

    print("raw_tail:")
    for mid in raw_lineage[-10:]:
        n = id_to_node[mid]
        preview = n.content.replace("\n", "\\n")[:100]
        print(f"  {mid} parent={n.parent} role={n.role} preview={preview}")

    print("canon_tail:")
    for cid in canon_lineage[-10:]:
        n = canon_nodes[cid]
        preview = n.content.replace("\n", "\\n")[:100]
        print(f"  {cid} parent={n.parent} role={n.role} preview={preview}")

    # Near-n0 anomaly diagnostics: semantically startup-like content should be root.
    if "n0" in id_to_node:
        if args.normalize == "whitespace":
            base = normalize_whitespace_structural(id_to_node["n0"].content)
        else:
            base = id_to_node["n0"].content

        near_root: list[tuple[float, LegacyNode]] = []
        for n in nodes:
            if n.id == "n0":
                continue
            c = normalize_whitespace_structural(n.content) if args.normalize == "whitespace" else n.content
            ratio = SequenceMatcher(None, base, c).ratio()
            if ratio >= args.near_root_threshold:
                near_root.append((ratio, n))

        near_root.sort(key=lambda t: (-t[0], int(t[1].id[1:]) if t[1].id[1:].isdigit() else 10**12))

        non_root_near = [(r, n) for (r, n) in near_root if n.parent is not None]
        print(f"near_root_matches={len(near_root)} threshold={args.near_root_threshold}")
        print(f"near_root_non_root_anomalies={len(non_root_near)}")

        if non_root_near:
            print("near_root_non_root_sample:")
            for ratio, n in non_root_near[: max(0, args.near_root_limit)]:
                parent = n.parent
                pparent = id_to_node[parent].parent if isinstance(parent, str) and parent in id_to_node else None
                # Small focused diff snippet (first differing offset)
                a = base
                b = normalize_whitespace_structural(n.content) if args.normalize == "whitespace" else n.content
                idx = None
                m = min(len(a), len(b))
                for i in range(m):
                    if a[i] != b[i]:
                        idx = i
                        break
                if idx is None and len(a) != len(b):
                    idx = m
                if idx is None:
                    idx = 0
                lo = max(0, idx - 35)
                hi = idx + 70
                a_snip = a[lo:hi].replace("\n", "\\n")
                b_snip = b[lo:hi].replace("\n", "\\n")
                print(
                    f"  {n.id} parent={parent} grandparent={pparent} role={n.role} "
                    f"len={len(n.content)} sim={ratio:.4f} diff_at={idx}"
                )
                print(f"    n0: {a_snip}")
                print(f"    {n.id}: {b_snip}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
