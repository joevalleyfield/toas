from __future__ import annotations


def run_intents_local(*, ensure_file, resolve_events_path, read_log, intent_records, active_intent, print_fn=print):
    ensure_file(resolve_events_path())
    events = read_log(str(resolve_events_path()))
    intents = intent_records(events)
    current = active_intent(events)
    if not intents:
        print_fn("intents: (none)")
        return
    print_fn("intents:")
    for event in intents[-20:]:
        payload = event["payload"]
        marker = "*" if current is event else " "
        print_fn(f"{marker} {payload['intent_id']} [{payload['status']}] {payload['title']}")


def run_history_local(*, ensure_file, resolve_events_path, operator_history_lines, limit: int = 10, print_fn=print):
    ensure_file(resolve_events_path())
    for line in operator_history_lines(events_path=resolve_events_path(), limit=limit).lines:
        print_fn(line)


def run_rebuild_local(*, ensure_file, resolve_events_path, operator_rebuild_session, head_id=None, print_fn=print):
    ensure_file(resolve_events_path())
    out = operator_rebuild_session(events_path=resolve_events_path(), head_id=head_id)
    print_fn(f"rebuilt {out.session_path.as_posix()} from head {out.target_label}")


def run_session_path_local(*, ensure_file, resolve_events_path, read_log, resolve_session_path, print_fn=print):
    ensure_file(resolve_events_path())
    events = read_log(str(resolve_events_path()))
    print_fn(resolve_session_path(events).as_posix())


def run_prompts_local(*, list_prompt_assets, prefix: str | None = None, print_fn=print):
    for asset in list_prompt_assets(prefix):
        name = asset.metadata.get("name", asset.ref.rsplit("/", 1)[-1])
        description = asset.metadata.get("description", "")
        category = asset.metadata.get("category")
        if category:
            print_fn(f"{asset.ref}\t[{category}] {name}\t{description}")
        else:
            print_fn(f"{asset.ref}\t{name}\t{description}")
