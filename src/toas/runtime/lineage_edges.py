def find_common_ancestor(lineage_a: list[dict], lineage_b: list[dict]) -> dict | None:
    ids_b = {event["id"] for event in lineage_b if "id" in event}
    for event in reversed(lineage_a):
        if event.get("id") in ids_b:
            return event
    return None


def first_after(lineage: list[dict], ancestor_id: str) -> dict | None:
    for index, event in enumerate(lineage):
        if event.get("id") == ancestor_id:
            return lineage[index + 1] if index + 1 < len(lineage) else None
    return None


def format_common_ancestor_line(*, ancestor_id: str, marker: str, preview: str) -> str:
    return f"common ancestor: {ancestor_id}  {marker}  \"{preview}\""


def format_branch_header(*, label: str, head_id: str) -> str:
    return f"branch {label} (head {head_id}):"


def format_no_diverging_line() -> str:
    return "  (no diverging message)"


def format_diverging_line(*, event_id: str, role: str, marker: str, preview: str) -> str:
    return f"  {event_id}  {role.upper()}  {marker}  \"{preview}\""


def format_ancestry_line(*, event_id: str, role: str, marker: str, display: str) -> str:
    return f"{event_id}  {role.upper()}  {marker}  {display}"
