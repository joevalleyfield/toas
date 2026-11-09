from toas.graph_control_state_edges import (
    active_config_overrides,
    active_policy_state,
    active_shell_scope_grants,
    active_surface_id,
    active_target_selection,
    active_workspace_scope,
    deep_delete,
    surface_bindings,
)


def test_active_target_selection_tracks_set_and_unset_events():
    events = [
        {"kind": "target_selection", "payload": {"action": "set", "target_id": "one"}},
        {"kind": "target_selection", "payload": {"action": "set", "target_id": " two "}},
        {"kind": "target_selection", "payload": {"action": "unset"}},
    ]
    assert active_target_selection(events) is None
    assert active_target_selection(events[:2]) == "two"


def test_active_target_selection_ignores_invalid_events():
    assert active_target_selection(
        [
            {"kind": "target_selection", "payload": "bad"},
            {"kind": "target_selection", "payload": {"action": "set", "target_id": ""}},
            {"kind": "other", "payload": {"action": "set", "target_id": "x"}},
            {"kind": "target_selection", "related_to": "msg_legacy_tgt", "payload": {"action": "set", "target_id": "valid"}},
        ]
    ) == "valid"


def test_active_workspace_scope_ignores_empty_normalized_roots():
    events = [
        {"kind": "other"},
        {"kind": "workspace_scope", "payload": {"mode": "unbounded", "roots": [""]}},
    ]

    mode, roots = active_workspace_scope(events)
    assert mode == "unbounded"
    assert roots


def test_active_shell_scope_grants_normalizes_legacy_head_scope():
    events = [
        {"kind": "shell_scope_grant", "payload": {"scope": "head", "action": "add", "grant": "echo"}},
    ]
    state = active_shell_scope_grants(events)
    assert state["session"]["added"] == {"echo"}


def test_active_surface_id_ignores_non_matching_events():
    events = [
        {"kind": "other"},
        {"kind": "surface_select", "payload": {"surface_id": "surf-1"}},
    ]
    assert active_surface_id(events) == "surf-1"
    events = [
        {"kind": "shell_scope_grant", "related_to": "msg_add", "payload": {"scope": "session", "action": "add", "grant": "x"}},
        {"kind": "shell_scope_grant", "related_to": "msg_rm", "payload": {"scope": "session", "action": "remove", "grant": "x"}},
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
        {"kind": "config_override", "related_to": "msg_cfg", "payload": {"foo": {"bar": 1}}},
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


def test_surface_bindings_ignores_non_dict_payload():
    events = [
        {"kind": "surface_bind", "payload": "not-a-dict"},
    ]
    assert surface_bindings(events) == {}


def test_surface_bindings_ignores_missing_transcript_path():
    events = [
        {"kind": "surface_bind", "payload": {"surface_id": "s1", "transcript_path": None}},
    ]
    assert surface_bindings(events) == {}


def test_surface_bindings_ignores_empty_transcript_path():
    events = [
        {"kind": "surface_bind", "payload": {"surface_id": "s1", "transcript_path": ""}},
    ]
    assert surface_bindings(events) == {}


def test_active_surface_id_ignores_non_dict_payload():
    events = [
        {"kind": "surface_select", "payload": "not-a-dict"},
    ]
    assert active_surface_id(events) is None


def test_active_surface_id_ignores_empty_surface_id():
    events = [
        {"kind": "surface_select", "payload": {"surface_id": ""}},
    ]
    assert active_surface_id(events) is None


def test_active_policy_state_processes_policy_overrides():
    events = [
        {"kind": "policy_override", "payload": "not-a-dict"},
        {"kind": "policy_override", "payload": {"key": "", "scope": "session", "action": "set"}},
        {"kind": "policy_override", "payload": {"key": "shell.allowed", "scope": "invalid", "action": "add"}},
        {"kind": "policy_override", "payload": {"key": "shell.allowed", "scope": "session", "action": "add", "value": "git"}},
        {"kind": "policy_override", "payload": {"key": "shell.allowed", "scope": "session", "action": "add", "value": ["cargo", "pytest"]}},
        {"kind": "policy_override", "payload": {"key": "shell.allowed", "scope": "session", "action": "remove", "value": "cargo"}},
        {"kind": "policy_override", "payload": {"key": "shell.allowed", "scope": "session", "action": "reset"}},
        {"kind": "policy_override", "related_to": "msg_sh", "payload": {"key": "shell.allowed", "scope": "session", "action": "add", "value": "sh"}},
        {"kind": "policy_override", "related_to": "msg_rm", "payload": {"key": "shell.allowed", "scope": "session", "action": "remove", "value": ["other", "echo"]}},
        {"kind": "policy_override", "payload": {"key": "llm.target", "scope": "workspace", "action": "set", "value": "gpt-4o"}},
        {"kind": "policy_override", "payload": {"key": "llm.target", "scope": "workspace", "action": "unset"}},
        {"kind": "policy_override", "related_to": "msg_tgt", "payload": {"key": "llm.target", "scope": "user", "action": "set", "value": "claude-3-5"}},
        {"kind": "policy_override", "payload": {"key": "model.name", "scope": "global", "action": "set", "value": "deepseek"}},
        {"kind": "policy_override", "payload": {"key": "model.name", "scope": "global", "action": "unset"}},
        {"kind": "policy_override", "related_to": "msg_sys", "payload": {"key": "system.prompt", "scope": "workspace", "action": "set", "value": "hello"}},
    ]
    state = active_policy_state(events)
    assert state["shell_grants"]["session"]["added"] == {"sh"}
    assert state["scalars"]["user"]["llm.target"] == "claude-3-5"
    assert active_target_selection(events) == "claude-3-5"
    assert state["config_overrides"]["system"] == {"prompt": "hello"}
    assert state["config_overrides"]["llm"] == {"target": "claude-3-5"}
    assert "sh" in state["config_overrides"]["shell"]["allowed_commands"]
    assert "echo" not in state["config_overrides"]["shell"]["allowed_commands"]
    assert state["sources"]["system.prompt"] == {"scope": "workspace", "source_id": "msg_sys"}
    assert state["sources"]["llm.target"] == {"scope": "user", "source_id": "msg_tgt"}
    assert state["scopes"]["session"]["collections"]["shell.allowed_commands"]["sources"]["sh"] == "msg_sh"


def test_active_policy_state_restore_action():
    events = [
        {"kind": "policy_override", "payload": {"key": "foo.bar", "scope": "session", "action": "set", "value": 1}},
        {"kind": "policy_override", "payload": {"key": "any", "scope": "session", "action": "restore"}},
    ]
    state = active_policy_state(events)
    assert state["config_overrides"] == {}
    assert state["scalars"]["session"] == {}


def test_resolve_lineage_ids_behaviors():
    from toas.graph_control_state_edges import _resolve_lineage_ids

    assert _resolve_lineage_ids([], lineage_ids={"n1", "n2"}) == {"n1", "n2"}
    assert _resolve_lineage_ids([{"kind": "other"}]) is None

    events = [
        {"id": "n1", "role": "user", "content": "hi", "parent": None},
        {"id": "n2", "role": "assistant", "content": "hello", "parent": "n1"},
        {"id": "n3", "role": "user", "content": "branch a", "parent": "n2"},
        {"id": "n4", "role": "user", "content": "branch b", "parent": "n2"},
    ]
    assert _resolve_lineage_ids(events, head_id="n3") == {"n1", "n2", "n3"}
    assert _resolve_lineage_ids(events, head_id="n4") == {"n1", "n2", "n4"}
    assert _resolve_lineage_ids(events, head_id=None) == {"n1", "n2", "n4"}


def test_active_policy_state_isolates_by_branch_lineage(tmp_path):
    from toas.graph_control_state_edges import active_command_context

    root_a = str(tmp_path / "branch" / "a" / "root")
    root_b = str(tmp_path / "branch" / "b" / "root")
    events = [
        {"id": "n1", "role": "user", "content": "root", "parent": None},
        {"id": "n2", "role": "assistant", "content": "response", "parent": "n1"},
        # Ancestor policy
        {"kind": "policy_override", "related_to": "n1", "payload": {"key": "ancestor.key", "scope": "session", "action": "set", "value": "ancestor_val"}},
        # Sibling branch A (n3)
        {"id": "n3", "role": "user", "content": "branch A", "parent": "n2"},
        {"kind": "policy_override", "related_to": "n3", "payload": {"key": "session.telemetry_decorations", "scope": "session", "action": "set", "value": "compact"}},
        {"kind": "target_selection", "related_to": "n3", "payload": {"action": "set", "target_id": "target_a"}},
        {"kind": "shell_scope_grant", "related_to": "n3", "payload": {"scope": "session", "action": "add", "grant": "branch_a_cmd"}},
        {"kind": "command_context", "related_to": "n3", "payload": {"cwd": "/branch/a"}},
        {"kind": "workspace_scope", "related_to": "n3", "payload": {"mode": "unbounded", "roots": [root_a]}},
        # Sibling branch B (n4)
        {"id": "n4", "role": "user", "content": "branch B", "parent": "n2"},
        {"kind": "policy_override", "related_to": "n4", "payload": {"key": "session.telemetry_decorations", "scope": "session", "action": "set", "value": "off"}},
        {"kind": "target_selection", "related_to": "n4", "payload": {"action": "set", "target_id": "target_b"}},
        {"kind": "shell_scope_grant", "related_to": "n4", "payload": {"scope": "session", "action": "add", "grant": "branch_b_cmd"}},
        {"kind": "command_context", "related_to": "n4", "payload": {"cwd": "/branch/b"}},
        {"kind": "workspace_scope", "related_to": "n4", "payload": {"mode": "strict", "roots": [root_b]}},
        # Legacy unlinked fallback
        {"kind": "policy_override", "payload": {"key": "legacy.key", "scope": "global", "action": "set", "value": "fallback"}},
    ]

    state_a = active_policy_state(events, head_id="n3")
    assert state_a["effective"]["ancestor.key"] == "ancestor_val"
    assert state_a["effective"]["session.telemetry_decorations"] == "compact"
    assert state_a["effective"]["legacy.key"] == "fallback"
    assert state_a["sources"]["session.telemetry_decorations"] == {"scope": "session", "source_id": "n3"}
    assert active_target_selection(events, head_id="n3") == "target_a"
    assert active_shell_scope_grants(events, head_id="n3")["session"]["added"] == {"branch_a_cmd"}
    cwd_a, _ = active_command_context(events, head_id="n3")
    assert cwd_a == "/branch/a"
    mode_a, roots_a = active_workspace_scope(events, head_id="n3")
    assert mode_a == "unbounded"
    assert roots_a == [root_a]

    state_b = active_policy_state(events, head_id="n4")
    assert state_b["effective"]["ancestor.key"] == "ancestor_val"
    assert state_b["effective"]["session.telemetry_decorations"] == "off"
    assert state_b["effective"]["legacy.key"] == "fallback"
    assert state_b["sources"]["session.telemetry_decorations"] == {"scope": "session", "source_id": "n4"}
    assert active_target_selection(events, head_id="n4") == "target_b"
    assert active_shell_scope_grants(events, head_id="n4")["session"]["added"] == {"branch_b_cmd"}
    cwd_b, _ = active_command_context(events, head_id="n4")
    assert cwd_b == "/branch/b"
    mode_b, roots_b = active_workspace_scope(events, head_id="n4")
    assert mode_b == "strict"
    assert roots_b == [root_b]

