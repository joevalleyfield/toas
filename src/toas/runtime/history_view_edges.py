def head_marker(*, head_id: str, selected_head_id: str | None) -> str:
    return "*" if head_id == selected_head_id else " "


def head_first_line(content: str) -> str:
    lines = content.splitlines()
    if not lines:
        return ""
    for line in lines:
        stripped = line.strip()
        if _is_low_signal_preview_line(stripped):
            continue
        return line
    return lines[0]


def _is_low_signal_preview_line(stripped_line: str) -> bool:
    if not stripped_line:
        return True
    if stripped_line == "## RESULT":
        return True
    return stripped_line.startswith("```") or stripped_line.startswith("~~~")


def build_heads_row_input(
    *,
    head: dict,
    selected_head_id: str | None,
    depth: int,
    turns: int,
    provenance_summary: str,
) -> dict:
    return {
        "marker": head_marker(head_id=head["id"], selected_head_id=selected_head_id),
        "head_id": head["id"],
        "role": head["role"],
        "first_line": head_first_line(str(head.get("content", ""))),
        "depth": depth,
        "turns": turns,
        "provenance_summary": provenance_summary,
    }
