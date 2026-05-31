import pytest

from toas.runtime.event_classification import (
    event_policy,
    is_ephemeral_event,
    is_terminal_event,
    should_persist_event,
    should_project_event,
)


def test_event_policy_known_kinds():
    assert should_persist_event("request") is True
    assert should_project_event("request") is False
    assert is_ephemeral_event("request") is False

    assert should_persist_event("progress") is False
    assert should_project_event("progress") is False
    assert is_ephemeral_event("progress") is True

    assert should_persist_event("stdout") is False
    assert should_project_event("stdout") is True
    assert is_ephemeral_event("stdout") is False


def test_terminal_policy_by_kind_and_final_flag():
    assert is_terminal_event("result") is True
    assert is_terminal_event("error") is True
    assert is_terminal_event("cancelled") is True
    assert is_terminal_event("status") is False
    assert is_terminal_event("status", final_flag=True) is True


def test_llm_done_alias_supported_for_existing_stream_shape():
    policy = event_policy("llm_done")
    assert policy.terminal is True
    assert policy.projected is True


def test_run_done_classified_as_terminal_projected_outcome():
    policy = event_policy("run_done")
    assert policy.terminal is True
    assert policy.projected is True
    assert should_persist_event("run_done") is True


def test_projection_events_classified_as_projected_nonterminal_events():
    policy = event_policy("projection_delta")
    assert policy.terminal is False
    assert policy.projected is True
    assert should_persist_event("projection_delta") is False
    done_policy = event_policy("projection_done")
    assert done_policy.terminal is False
    assert done_policy.projected is True
    assert should_persist_event("projection_done") is False


def test_daemon_stream_event_kinds_are_classified():
    assert should_project_event("llm_delta") is True
    assert should_project_event("llm_reasoning") is True
    assert is_terminal_event("llm_reasoning") is False
    assert is_ephemeral_event("prompt_progress") is True
    assert should_project_event("tool_progress") is True
    assert should_project_event("tool_done") is True
    assert should_project_event("projection_delta") is True
    assert should_project_event("projection_done") is True


def test_unknown_event_kind_raises():
    with pytest.raises(ValueError, match="unknown event kind"):
        event_policy("mystery")
