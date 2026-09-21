"""Executable worked histories for transcript-policy reinterpretation.

These deliberately exercise the local step boundary instead of unit-testing a
future reducer.  The strict xfails are proposed contracts, kept next to the
current baselines so a policy-lineage design has concrete behavior to satisfy.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import toas.cli as cli

ASSISTANT_PLAN = """## TOAS:ASSISTANT
```yaml
- operation: shell
  arguments:
    argv: [\"sh\", \"-c\", \"printf policy-example\"]
```
"""

TIMEOUT_PLAN = """## TOAS:ASSISTANT
```yaml
- operation: shell
  arguments:
    argv: ["echo", "policy-timeout"]
```
"""


def _events(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _message_events(events: list[dict]) -> list[dict]:
    return [event for event in events if isinstance(event.get("id"), str) and isinstance(event.get("role"), str)]


def _assistant_results(events: list[dict]) -> list[dict]:
    message_by_id = {event["id"]: event for event in _message_events(events)}
    return [
        event
        for event in events
        if event.get("kind") == "tool_result"
        and message_by_id.get(event.get("related_to"), {}).get("role") == "assistant"
    ]


def _step(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, transcript: str) -> list[dict]:
    monkeypatch.chdir(tmp_path)
    events_path = tmp_path / ".toas" / "events.jsonl"
    events_path.parent.mkdir(exist_ok=True)
    (tmp_path / ".toas" / "session.md").write_text(transcript, encoding="utf-8")
    monkeypatch.setattr(cli, "_rpc_stdout", lambda _op: False)
    cli._run_step()
    return _events(events_path)


def test_earlier_nonpolicy_edit_retains_a_recreated_policy_delta(monkeypatch, tmp_path, fake_shell_subprocess):
    """Current behavior keeps policy after a harmless edit before its control."""
    _step(monkeypatch, tmp_path, "## TOAS:USER\nP0 original wording\n\n## TOAS:CONTROL\n/shell add sh\n")

    events = _step(
        monkeypatch,
        tmp_path,
        "## TOAS:USER\nP0 corrected wording only\n\n## TOAS:CONTROL\n/shell add sh\n\n" + ASSISTANT_PLAN,
    )

    messages = _message_events(events)
    corrected = next(event for event in messages if event["content"] == "P0 corrected wording only")
    recreated_control = next(event for event in messages if event["parent"] == corrected["id"] and event["role"] == "control")
    assistant = [event for event in messages if event["role"] == "assistant"][-1]
    assert assistant["parent"] == recreated_control["id"]
    assert _assistant_results(events)[-1]["payload"]["ok"] is True


def test_direct_control_records_link_their_source_message(monkeypatch, tmp_path):
    events = _step(monkeypatch, tmp_path, "## TOAS:CONTROL\n/config set shell.assistant_timeout_s 900\n")

    source = _message_events(events)[-1]
    override = next(event for event in events if event.get("kind") == "config_override")
    assert override["related_to"] == source["id"]


def test_inserted_config_timeout_applies_to_restepped_assistant(monkeypatch, tmp_path, fake_shell_subprocess):
    _step(monkeypatch, tmp_path, "## TOAS:USER\nP0\n\n" + TIMEOUT_PLAN)

    _step(
        monkeypatch,
        tmp_path,
        "## TOAS:USER\nP0\n\n## TOAS:CONTROL\n/config set shell.assistant_timeout_s 900\n\n" + TIMEOUT_PLAN,
    )

    assert fake_shell_subprocess.call_args.kwargs["timeout_s"] == 900


def test_config_delta_on_one_sibling_does_not_change_another_sibling(monkeypatch, tmp_path, fake_shell_subprocess):
    _step(monkeypatch, tmp_path, "## TOAS:USER\nP0\n\n## TOAS:CONTROL\n/config set shell.assistant_timeout_s 900\n")

    _step(monkeypatch, tmp_path, "## TOAS:USER\nP0\n\n" + TIMEOUT_PLAN)

    assert fake_shell_subprocess.call_args.kwargs["timeout_s"] == 5


def test_restep_after_inserted_control_creates_related_assistant_under_new_policy(monkeypatch, tmp_path, fake_shell_subprocess):
    """Desired recovery: P1 changes policy for A2 without regenerating A1."""
    before = _step(monkeypatch, tmp_path, "## TOAS:USER\nP0\n\n" + ASSISTANT_PLAN)
    original = [event for event in _message_events(before) if event["role"] == "assistant"][-1]

    events = _step(
        monkeypatch,
        tmp_path,
        "## TOAS:USER\nP0\n\n## TOAS:CONTROL\n/shell add sh\n\n" + ASSISTANT_PLAN,
    )

    restep = [event for event in _message_events(events) if event["role"] == "assistant"][-1]
    assert restep["provenance"]["restep_of"] == original["id"]
    assert _assistant_results(events)[-1]["payload"]["ok"] is True


def test_policy_delta_on_one_sibling_does_not_authorize_another_sibling(monkeypatch, tmp_path, fake_shell_subprocess):
    """Desired isolation: a P1 grant is visible only below its branch."""
    _step(monkeypatch, tmp_path, "## TOAS:USER\nP0\n\n## TOAS:CONTROL\n/shell add sh\n")

    events = _step(monkeypatch, tmp_path, "## TOAS:USER\nP0\n\n" + ASSISTANT_PLAN)

    assert _assistant_results(events)[-1]["payload"]["ok"] is False


def test_inserted_cd_applies_to_restepped_assistant(monkeypatch, tmp_path, fake_shell_subprocess):
    target = tmp_path / "target"
    target.mkdir()

    _step(
        monkeypatch,
        tmp_path,
        "## TOAS:USER\nP0\n\n"
        f"## TOAS:CONTROL\n/cd {target}\n\n"
        "## TOAS:CONTROL\n/shell add sh\n\n"
        + ASSISTANT_PLAN,
    )

    assert Path(fake_shell_subprocess.call_args.kwargs["cwd"]) == target


def test_cd_on_one_sibling_does_not_change_another_sibling(monkeypatch, tmp_path, fake_shell_subprocess):
    target = tmp_path / "target"
    target.mkdir()
    _step(monkeypatch, tmp_path, f"## TOAS:USER\nP0\n\n## TOAS:CONTROL\n/cd {target}\n")

    _step(
        monkeypatch,
        tmp_path,
        "## TOAS:USER\nP0\n\n## TOAS:CONTROL\n/shell add sh\n\n" + ASSISTANT_PLAN,
    )

    assert Path(fake_shell_subprocess.call_args.kwargs["cwd"]) == tmp_path


def test_cd_context_record_links_its_source_message(monkeypatch, tmp_path):
    target = tmp_path / "target"
    target.mkdir()
    events = _step(monkeypatch, tmp_path, f"## TOAS:CONTROL\n/cd {target}\n")

    source = next(event for event in _message_events(events) if event["content"] == f"/cd {target}")
    record = next(event for event in events if event.get("kind") == "command_context")
    assert record["related_to"] == source["id"]


def test_workspace_add_allows_cd_before_restepped_assistant(monkeypatch, tmp_path, fake_shell_subprocess):
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir()
    _step(
        monkeypatch,
        tmp_path,
        "## TOAS:USER\nP0\n\n"
        f"## TOAS:CONTROL\n/workspace add {outside}\n\n"
        f"## TOAS:CONTROL\n/cd {outside}\n\n"
        "## TOAS:CONTROL\n/shell add sh\n\n"
        + ASSISTANT_PLAN,
    )

    assert Path(fake_shell_subprocess.call_args.kwargs["cwd"]) == outside


def test_workspace_add_on_one_sibling_does_not_expand_another(monkeypatch, tmp_path, fake_shell_subprocess):
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir()
    _step(monkeypatch, tmp_path, f"## TOAS:USER\nP0\n\n## TOAS:CONTROL\n/workspace add {outside}\n")

    _step(
        monkeypatch,
        tmp_path,
        "## TOAS:USER\nP0\n\n"
        f"## TOAS:CONTROL\n/cd {outside}\n\n"
        "## TOAS:CONTROL\n/shell add sh\n\n"
        + ASSISTANT_PLAN,
    )

    assert Path(fake_shell_subprocess.call_args.kwargs["cwd"]) == tmp_path
