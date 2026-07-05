from .lineage_edges import (
    find_common_ancestor,
    first_after,
    format_ancestry_line,
    format_branch_header,
    format_common_ancestor_line,
    format_diverging_line,
    format_no_diverging_line,
)


def build_diff_lines(
    *,
    head_a: str,
    head_b: str,
    lineage_a: list[dict],
    lineage_b: list[dict],
    full: bool,
    provenance_marker_fn,
    content_preview_fn,
) -> list[str]:
    if head_a == head_b:
        ancestor = lineage_a[-1]
        marker = provenance_marker_fn(ancestor)
        preview = content_preview_fn(str(ancestor.get("content", "")), full=full)
        return [
            format_common_ancestor_line(ancestor_id=ancestor["id"], marker=marker, preview=preview),
            "",
            "branch A and branch B are the same head",
        ]

    common_ancestor: dict[str, object] | None = find_common_ancestor(lineage_a, lineage_b)
    if common_ancestor is None:
        raise SystemExit(f"no common ancestor between {head_a} and {head_b}")

    ancestor_id = str(common_ancestor["id"])
    marker = provenance_marker_fn(common_ancestor)
    preview = content_preview_fn(str(common_ancestor.get("content", "")), full=full)
    lines = [format_common_ancestor_line(ancestor_id=ancestor_id, marker=marker, preview=preview), ""]

    for label, head_id, lineage in (("A", head_a, lineage_a), ("B", head_b, lineage_b)):
        lines.append(format_branch_header(label=label, head_id=head_id))
        diverging = first_after(lineage, ancestor_id)
        if diverging is None:
            lines.append(format_no_diverging_line())
        else:
            lines.append(
                format_diverging_line(
                    event_id=diverging["id"],
                    role=str(diverging.get("role", "?")),
                    marker=provenance_marker_fn(diverging),
                    preview=content_preview_fn(str(diverging.get("content", "")), full=full),
                )
            )
        lines.append("")

    return lines


def build_ancestry_lines(
    *,
    lineage: list[dict],
    depth: int | None,
    full: bool,
    provenance_marker_fn,
    content_preview_fn,
) -> list[str]:
    chain = lineage[-depth:] if depth is not None else lineage
    return [
        format_ancestry_line(
            event_id=str(event.get("id", "?")),
            role=str(event.get("role", "?")),
            marker=provenance_marker_fn(event),
            display=content_preview_fn(str(event.get("content", "")), full=full),
        )
        for event in chain
    ]
