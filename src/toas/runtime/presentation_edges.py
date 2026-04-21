def render_output_with_newline_style(
    *,
    rendered: str,
    newline: str,
    apply_newline_style_fn,
) -> str:
    if not rendered:
        return ""
    return apply_newline_style_fn(rendered, newline)


def extract_response_stdout(response: dict) -> str:
    return str(response.get("stdout", ""))


def format_heads_row(
    *,
    marker: str,
    head_id: str,
    role: str,
    first_line: str,
    depth: int,
    turns: int,
    provenance_summary: str,
) -> str:
    return f"{marker} {head_id} {role}: {first_line}  [d={depth} t={turns} {provenance_summary}]"


def format_selected_head_line(selected: str | None) -> str:
    return f"selected_head={selected or '-'}"


def format_bind_index_line(bind_index: int | None) -> str:
    return f"bind_index={bind_index if bind_index is not None else '-'}"


def format_history_head_row(*, marker: str, head_id: str, role: str) -> str:
    return f"{marker} {head_id} {role}"


def format_recent_event_row(summary: str) -> str:
    return f"- {summary}"
