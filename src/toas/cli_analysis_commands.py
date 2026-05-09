from __future__ import annotations


def run_diff_local(
    *,
    ensure_file,
    resolve_events_path,
    read_log,
    message_lineage,
    build_runtime_diff_lines,
    provenance_marker_fn,
    format_content_fn,
    head_a: str,
    head_b: str,
    full: bool = False,
    print_fn=print,
):
    ensure_file(resolve_events_path())
    events = read_log(str(resolve_events_path()))
    lineage_a = message_lineage(events, head_id=head_a)
    lineage_b = message_lineage(events, head_id=head_b)
    if not lineage_a:
        raise SystemExit(f"no message found with id: {head_a}")
    if not lineage_b:
        raise SystemExit(f"no message found with id: {head_b}")
    for line in build_runtime_diff_lines(
        head_a=head_a,
        head_b=head_b,
        lineage_a=lineage_a,
        lineage_b=lineage_b,
        full=full,
        provenance_marker_fn=provenance_marker_fn,
        content_preview_fn=format_content_fn,
    ):
        print_fn(line)


def run_ancestry_local(
    *,
    ensure_file,
    resolve_events_path,
    read_log,
    message_lineage,
    build_runtime_ancestry_lines,
    provenance_marker_fn,
    format_content_preview_fn,
    message_id: str,
    depth: int | None = None,
    full: bool = False,
    print_fn=print,
):
    ensure_file(resolve_events_path())
    events = read_log(str(resolve_events_path()))
    lineage = message_lineage(events, head_id=message_id)
    if not lineage:
        raise SystemExit(f"no message found with id: {message_id}")
    for line in build_runtime_ancestry_lines(
        lineage=lineage,
        depth=depth,
        full=full,
        provenance_marker_fn=provenance_marker_fn,
        content_preview_fn=format_content_preview_fn,
    ):
        print_fn(line)


def run_index_rebuild_local(
    *,
    resolve_events_path,
    ensure_file,
    read_log,
    rebuild_index,
    print_fn=print,
):
    events_path = resolve_events_path()
    ensure_file(events_path)
    events = read_log(str(events_path))
    message_count = sum(1 for e in events if "role" in e and "content" in e and "id" in e)
    index_path = events_path.with_suffix(".idx")
    rebuild_index(str(events_path), str(index_path))
    print_fn(f"rebuilt {index_path.as_posix()} ({message_count} message event(s) indexed)")
