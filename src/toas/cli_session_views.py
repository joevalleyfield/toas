from __future__ import annotations


def run_history(*, ensure_file, resolve_events_path, operator_history_lines, limit: int = 10, print_fn=print):
    ensure_file(resolve_events_path())
    for line in operator_history_lines(events_path=resolve_events_path(), limit=limit).lines:
        print_fn(line)


def run_session_path(*, ensure_file, resolve_events_path, read_log, resolve_session_path, print_fn=print):
    ensure_file(resolve_events_path())
    events = read_log(str(resolve_events_path()))
    print_fn(resolve_session_path(events).as_posix())


def run_graph(
    *,
    ensure_file,
    resolve_events_path,
    operator_graph_text,
    projection: str = "temporal",
    source_tokens: list[str] | None = None,
    print_fn=print,
):
    ensure_file(resolve_events_path())
    out = operator_graph_text(
        events_path=resolve_events_path(),
        projection=projection,
        source_tokens=source_tokens,
    )
    print_fn(out.text)


def run_prompts(*, list_prompt_assets, prefix: str | None = None, print_fn=print):
    for asset in list_prompt_assets(prefix):
        name = asset.metadata.get("name", asset.ref.rsplit("/", 1)[-1])
        description = asset.metadata.get("description", "")
        category = asset.metadata.get("category")
        if category:
            print_fn(f"{asset.ref}\t[{category}] {name}\t{description}")
        else:
            print_fn(f"{asset.ref}\t{name}\t{description}")
