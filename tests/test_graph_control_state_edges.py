from toas.graph_control_state_edges import (
    active_config_overrides,
    active_shell_scope_grants,
    active_workspace_scope,
    deep_delete,
)


def test_active_workspace_scope_ignores_empty_normalized_roots():
    events = [
        {"kind": "workspace_scope", "payload": {"mode": "unbounded", "roots": [""]}},
    ]

    mode, roots = active_workspace_scope(events)
    assert mode == "unbounded"
    assert roots


def test_active_shell_scope_grants_remove_discards_previously_added_grant():
    events = [
        {"kind": "shell_scope_grant", "payload": {"scope": "session", "action": "add", "grant": "x"}},
        {"kind": "shell_scope_grant", "payload": {"scope": "session", "action": "remove", "grant": "x"}},
    ]
    state = active_shell_scope_grants(events)
    assert state["session"]["added"] == set()
    assert state["session"]["removed"] == {"x"}


def test_active_shell_scope_grants_ignores_non_shell_scope_records():
    events = [
        {"kind": "anchor", "payload": {"offset": 1, "node_id": "n0"}},
    ]
    state = active_shell_scope_grants(events)
    assert state["session"]["added"] == set()
    assert state["session"]["removed"] == set()


def test_active_config_overrides_unset_ignores_non_string_key():
    events = [
        {"kind": "config_override", "payload": {"foo": {"bar": 1}}},
        {"kind": "config_override", "payload": {"__op__": "unset", "key": None}},
    ]
    assert active_config_overrides(events) == {"foo": {"bar": 1}}


def test_active_config_overrides_ignores_non_dict_payload():
    events = [
        {"kind": "config_override", "payload": "bad-shape"},
    ]
    assert active_config_overrides(events) == {}


def test_deep_delete_prunes_empty_parents():
    base = {"a": {"b": {"c": 1}}}
    assert deep_delete(base, "a.b.c") == {}


def test_deep_delete_returns_original_when_intermediate_is_not_dict():
    base = {"a": 1}
    assert deep_delete(base, "a.b") == base
