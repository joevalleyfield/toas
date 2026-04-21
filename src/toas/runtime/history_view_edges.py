def head_marker(*, head_id: str, selected_head_id: str | None) -> str:
    return "*" if head_id == selected_head_id else " "


def head_first_line(content: str) -> str:
    return content.splitlines()[0] if content else ""


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


def build_history_head_row_input(*, head: dict, selected_head_id: str | None) -> dict:
    return {
        "marker": head_marker(head_id=head["id"], selected_head_id=selected_head_id),
        "head_id": head["id"],
        "role": head["role"],
    }
