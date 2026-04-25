from __future__ import annotations

import shlex
from pathlib import Path

import pytest

from toas.config import BackendCatalogEntry, LLMPolicy, OperatorConfig
from toas.runtime.operator_command_config_help import (
    _config_secret_result,
    _resolve_config_path,
    _validate_known_config_key,
    handle_config_help_commands,
)
from toas.runtime.operator_command_context import OperatorCommandContext
from toas.runtime.operator_command_extract_replay import (
    _collect_replay_candidates,
    _latest_assistant_target,
    _parse_extract_selection,
    _parse_replay_args,
    _render_replay_candidates,
    handle_extract_replay_commands,
)
from toas.runtime.operator_command_prompt_workspace import (
    _handle_shell_config,
    _parse_compact_args,
    _resolve_cd_target,
    _resolve_workspace_arg,
    _validate_env_key,
    handle_prompt_workspace_commands,
)


def _ctx(**overrides):
    base = OperatorCommandContext(
        execute=lambda _working, _plan: [],
        events=[],
        working=[],
        transcript="",
        command_cwd=".",
        previous_command_cwd=None,
        workspace_mode="strict",
        workspace_roots=[str(Path(".").resolve())],
        config=OperatorConfig(),
        config_sources=None,
        already_executed_indices=None,
    )
    data = base.__dict__.copy()
    data.update(overrides)
    return OperatorCommandContext(**data)


def test_prompt_workspace_handler_prompts(monkeypatch):
    import toas.step as step_mod

    monkeypatch.setattr(step_mod, "_render_prompt_browse_commands", lambda prefix: f"rendered:{prefix}")
    out = handle_prompt_workspace_commands("prompts", ["x"], step_mod=step_mod, context=_ctx())
    assert out == [{"role": "result", "content": "rendered:x"}]


def test_extract_replay_handler_replay_dry_run(monkeypatch):
    import toas.step as step_mod

    monkeypatch.setattr(step_mod, "extract_plan_with_status", lambda _content, yaml_position="any": ([{"tool_name": "echo_block", "args": {"content": "x"}}], False))

    working = [
        {"role": "user", "content": "hello"},
        {"role": "user", "content": "/replay --index 1 --dry-run"},
    ]
    out = handle_extract_replay_commands("replay", ["--index", "1", "--dry-run"], step_mod=step_mod, context=_ctx(working=working))
    assert out is not None
    assert "replay dry-run" in out[0]["content"]


def test_config_help_handler_help(monkeypatch):
    import toas.step as step_mod

    monkeypatch.setattr(step_mod, "render_session_help", lambda: "help text")
    monkeypatch.setattr(step_mod, "render_help_commands_inert", lambda: "commands help text")
    monkeypatch.setattr(step_mod, "render_help_tools", lambda: "tools help text")
    monkeypatch.setattr(step_mod, "render_help_cli", lambda: "cli help text")
    out = handle_config_help_commands("help", [], step_mod=step_mod, context=_ctx())
    assert out == [{"role": "result", "content": "help text"}]
    out_commands = handle_config_help_commands("help", ["commands"], step_mod=step_mod, context=_ctx())
    assert out_commands == [{"role": "result", "content": "commands help text"}]
    out_tools = handle_config_help_commands("help", ["tools"], step_mod=step_mod, context=_ctx())
    assert out_tools == [{"role": "result", "content": "tools help text"}]
    out_cli = handle_config_help_commands("help", ["cli"], step_mod=step_mod, context=_ctx())
    assert out_cli == [{"role": "result", "content": "cli help text"}]
    with pytest.raises(ValueError, match="usage: /help"):
        handle_config_help_commands("help", ["bad"], step_mod=step_mod, context=_ctx())


def test_handlers_return_none_for_non_matching_command():
    import toas.step as step_mod

    context = _ctx()
    assert handle_prompt_workspace_commands("nope", [], step_mod=step_mod, context=context) is None
    assert handle_extract_replay_commands("nope", [], step_mod=step_mod, context=context) is None
    assert handle_config_help_commands("nope", [], step_mod=step_mod, context=context) is None


def test_prompt_workspace_cd_strict_workspace_guard(tmp_path):
    import toas.step as step_mod

    outside = tmp_path / "outside"
    outside.mkdir()
    context = _ctx(command_cwd=str(tmp_path), workspace_roots=[str(tmp_path / "inside")], workspace_mode="strict")
    with pytest.raises(ValueError, match="cwd outside allowed workspace roots"):
        handle_prompt_workspace_commands("cd", [str(outside)], step_mod=step_mod, context=context)


def test_prompt_workspace_env_set_unset_and_usage(monkeypatch):
    import toas.step as step_mod

    out = handle_prompt_workspace_commands("env", ["set", "ABC", "123"], step_mod=step_mod, context=_ctx())
    assert out == [{"role": "result", "content": "env set: ABC"}]
    out = handle_prompt_workspace_commands("env", ["unset", "ABC"], step_mod=step_mod, context=_ctx())
    assert out == [{"role": "result", "content": "env unset: ABC"}]
    with pytest.raises(ValueError, match="usage: /env"):
        handle_prompt_workspace_commands("env", ["bad"], step_mod=step_mod, context=_ctx())


def test_prompt_workspace_shell_config_add_remove_reset_and_errors(monkeypatch):
    import toas.step as step_mod

    monkeypatch.setattr(step_mod, "normalize_shell_grants", lambda grants: tuple(grants))
    monkeypatch.setattr(step_mod, "parse_shell_grant", lambda s: type("P", (), {"raw": s})())
    cfg = OperatorConfig()
    out = handle_prompt_workspace_commands("shell", ["config", "add", "jj"], step_mod=step_mod, context=_ctx(config=cfg))
    assert out[0]["config_update"]["shell"]["allowed_commands"]
    out = handle_prompt_workspace_commands("shell", ["config", "remove", "jj"], step_mod=step_mod, context=_ctx(config=cfg))
    assert "config baseline" in out[0]["content"]
    out = handle_prompt_workspace_commands("shell", ["config", "reset"], step_mod=step_mod, context=_ctx(config=cfg))
    assert "reset to defaults" in out[0]["content"]
    with pytest.raises(ValueError, match="usage:"):
        handle_prompt_workspace_commands("shell", ["config", "add"], step_mod=step_mod, context=_ctx(config=cfg))


def test_prompt_workspace_shell_list_and_reset(monkeypatch):
    import toas.step as step_mod

    monkeypatch.setattr(step_mod, "_resolve_shell_grants_with_sources", lambda _w, _c: (("echo",), ("echo",), {"config": "default"}, (), ()))
    monkeypatch.setattr(step_mod, "render_shell_policy_view", lambda *args: "policy-view")
    monkeypatch.setattr(step_mod, "resolve_effective_shell_allowed", lambda _w, _c: ("echo",))
    monkeypatch.setattr(step_mod, "parse_shell_grant", lambda s: type("P", (), {"raw": s})())
    out = handle_prompt_workspace_commands("shell", ["list"], step_mod=step_mod, context=_ctx())
    assert out == [{"role": "result", "content": "policy-view"}]
    out = handle_prompt_workspace_commands("shell", ["reset"], step_mod=step_mod, context=_ctx())
    assert "reset to config baseline" in out[0]["content"]


def test_prompt_workspace_workspace_modes_and_compact(monkeypatch, tmp_path):
    import toas.step as step_mod

    monkeypatch.setattr(step_mod, "_render_workspace_commands", lambda mode, roots: f"{mode}:{len(roots)}")
    monkeypatch.setattr(step_mod, "_compact_result_blocks", lambda transcript, threshold: ("x", [{"index": 1, "chars": 900}]))
    cwd = tmp_path
    add_dir = tmp_path / "add"
    add_dir.mkdir()
    out = handle_prompt_workspace_commands("workspace", [], step_mod=step_mod, context=_ctx(command_cwd=str(cwd)))
    assert out == [{"role": "result", "content": "strict:1"}]
    out = handle_prompt_workspace_commands("workspace", ["add", str(add_dir)], step_mod=step_mod, context=_ctx(command_cwd=str(cwd)))
    assert "workspace_update" in out[0]
    out = handle_prompt_workspace_commands("workspace", ["mode", "unbounded"], step_mod=step_mod, context=_ctx(command_cwd=str(cwd)))
    assert out[0]["workspace_update"]["mode"] == "unbounded"
    out = handle_prompt_workspace_commands("compact", ["--dry-run", "--threshold", "10"], step_mod=step_mod, context=_ctx(transcript="t"))
    assert "compact dry-run" in out[0]["content"]


def test_prompt_workspace_helper_compact_parse_and_cd_target(tmp_path):
    dry_run, threshold = _parse_compact_args(["--dry-run", "--threshold", "12"])
    assert (dry_run, threshold) == (True, 12)
    with pytest.raises(ValueError, match="usage: /compact"):
        _parse_compact_args(["--threshold"])
    with pytest.raises(ValueError, match="threshold must be >= 0"):
        _parse_compact_args(["--threshold", "-1"])

    prev = tmp_path / "prev"
    prev.mkdir()
    context = _ctx(command_cwd=str(tmp_path), previous_command_cwd=str(prev))
    assert _resolve_cd_target("-", context=context) == prev.resolve()
    rel = _resolve_cd_target("x", context=context)
    assert rel == (tmp_path / "x").resolve()


def test_extract_handler_errors_and_adopt(monkeypatch):
    import toas.step as step_mod

    with pytest.raises(ValueError, match="no prior assistant message"):
        handle_extract_replay_commands("extract", [], step_mod=step_mod, context=_ctx(working=[{"role": "user", "content": "x"}]))

    monkeypatch.setattr(step_mod, "_extract_frontier_assistant_candidates", lambda _c: ([], ["1. bad"]))
    with pytest.raises(ValueError, match="skipped callable-looking blocks"):
        handle_extract_replay_commands(
            "extract",
            [],
            step_mod=step_mod,
            context=_ctx(working=[{"role": "assistant", "content": "a"}, {"role": "user", "content": "/extract"}]),
        )

    monkeypatch.setattr(step_mod, "_extract_frontier_assistant_candidates", lambda _c: ([{"kind": "tool_plan", "preview": "p", "adopt": "a"}], []))
    out = handle_extract_replay_commands(
        "extract",
        ["1"],
        step_mod=step_mod,
        context=_ctx(working=[{"role": "assistant", "content": "a"}, {"role": "user", "content": "/extract 1"}]),
    )
    assert out[0]["role"] == "user"
    with pytest.raises(ValueError, match="index out of range"):
        handle_extract_replay_commands(
            "extract",
            ["9"],
            step_mod=step_mod,
            context=_ctx(working=[{"role": "assistant", "content": "a"}, {"role": "user", "content": "/extract 9"}]),
        )


def test_replay_errors_and_force_path(monkeypatch):
    import toas.step as step_mod

    monkeypatch.setattr(step_mod, "extract_plan_with_status", lambda _c, yaml_position="any": (None, False))
    monkeypatch.setattr(step_mod, "_extract_loose_command", lambda _c: ("echo hi", False))
    monkeypatch.setattr(step_mod, "shlex", shlex)
    monkeypatch.setattr(step_mod, "_as_nodes", lambda nodes: nodes)

    working = [{"role": "assistant", "content": "$ echo hi"}, {"role": "user", "content": "/replay"}]
    out = handle_extract_replay_commands(
        "replay",
        ["--index", "1", "--force"],
        step_mod=step_mod,
        context=_ctx(working=working, already_executed_indices={1}, execute=lambda _w, _p: [{"role": "result", "content": "ok"}]),
    )
    assert out[0]["replay_execution"]["target_message_index"] == 1

    with pytest.raises(ValueError, match="usage: /replay"):
        handle_extract_replay_commands("replay", ["--index"], step_mod=step_mod, context=_ctx(working=working))
    with pytest.raises(ValueError, match="index out of range"):
        handle_extract_replay_commands("replay", ["--index", "9"], step_mod=step_mod, context=_ctx(working=working))


def test_extract_replay_helper_parsers():
    assert _parse_extract_selection([]) == (None, False)
    assert _parse_extract_selection(["2"]) == (2, False)
    assert _parse_extract_selection(["--verbose"]) == (None, True)
    assert _parse_extract_selection(["--verbose", "2"]) == (2, True)
    with pytest.raises(ValueError, match="usage: /extract"):
        _parse_extract_selection(["a"])
    with pytest.raises(ValueError, match="usage: /extract"):
        _parse_extract_selection(["1", "2"])

    assert _parse_replay_args(["--dry-run", "--index", "3", "--force"]) == (True, True, 3, None)
    with pytest.raises(ValueError, match="usage: /replay"):
        _parse_replay_args(["--index"])
    assert _parse_replay_args(["--resume", "q2"]) == (False, False, None, ("resume", "q2"))
    with pytest.raises(ValueError, match="usage: /replay"):
        _parse_replay_args(["--index", "1", "--resume", "q2"])


def test_config_show_sources_and_secret_usage(monkeypatch):
    import toas.step as step_mod

    monkeypatch.setattr(step_mod, "flatten_config", lambda _c: {"llm.model": "x"})
    out = handle_config_help_commands("config", ["show", "--sources"], step_mod=step_mod, context=_ctx(config_sources={"llm.model": "env"}))
    assert "[source=env]" in out[0]["content"]
    with pytest.raises(ValueError, match="usage: /config secret"):
        handle_config_help_commands("config", ["secret", "set", "llm_api_key"], step_mod=step_mod, context=_ctx())


def test_config_set_unset_restore_load_save_backend(monkeypatch, tmp_path):
    import toas.step as step_mod

    monkeypatch.setattr(step_mod, "valid_config_keys", lambda: ["llm.model", "generation.thinking_mode", "generation.transport_mode"])
    monkeypatch.setattr(step_mod, "apply_dotted_override", lambda _c, _k, _v: OperatorConfig())
    monkeypatch.setattr(step_mod, "flatten_config", lambda _c: {"llm.model": "m", "generation.thinking_mode": "disabled"})
    monkeypatch.setattr(step_mod, "load_file_config", lambda _p: {"llm": {"model": "m"}})
    monkeypatch.setattr(step_mod.Settings, "from_env", classmethod(lambda cls: type("S", (), {"llm_base_url": "u", "llm_model": "m"})()))
    cfg = OperatorConfig()

    out = handle_config_help_commands("config", ["set", "llm.model", "q"], step_mod=step_mod, context=_ctx(config=cfg))
    assert out[0]["config_update"] == {"llm": {"model": "m"}}
    out = handle_config_help_commands("config", ["unset", "llm.model"], step_mod=step_mod, context=_ctx(config=cfg))
    assert out[0]["config_update"]["__op__"] == "unset"
    out = handle_config_help_commands("config", ["restore"], step_mod=step_mod, context=_ctx(config=cfg))
    assert out[0]["config_update"]["__op__"] == "restore"

    cfg_path = tmp_path / "toas.toml"
    cfg_path.write_text("x=1", encoding="utf-8")
    out = handle_config_help_commands("config", ["load", str(cfg_path)], step_mod=step_mod, context=_ctx(config=cfg, command_cwd=str(tmp_path)))
    assert out[0]["config_update"]
    out = handle_config_help_commands("config", ["save", "out.toml"], step_mod=step_mod, context=_ctx(config=cfg))
    assert out[0]["config_save"]["path"] == "out.toml"

    out = handle_config_help_commands("config", ["backend", "add", "b1", "http://x"], step_mod=step_mod, context=_ctx(config=cfg))
    assert out[0]["config_update"]["llm"]["backends"][0]["id"] == "b1"
    cfg_with_backend = OperatorConfig(llm=LLMPolicy(backends=(BackendCatalogEntry(id="b1", base_url="http://x"),)))
    out = handle_config_help_commands("config", ["backend", "set", "b1.model", "m2"], step_mod=step_mod, context=_ctx(config=cfg_with_backend))
    assert "updated backend" in out[0]["content"]
    out = handle_config_help_commands("config", ["backend", "capture", "b2"], step_mod=step_mod, context=_ctx(config=cfg_with_backend))
    assert "captured backend b2" in out[0]["content"]


def test_config_helper_secret_and_path_and_usage(monkeypatch, tmp_path):
    import toas.step as step_mod

    out = _config_secret_result(["secret", "show"])
    assert "secret keys" in out[0]["content"]
    with pytest.raises(ValueError, match="usage: /config secret"):
        _config_secret_result(["secret", "set", "llm_api_key"])

    ctx = _ctx(command_cwd=str(tmp_path))
    resolved = _resolve_config_path("toas.toml", context=ctx)
    assert resolved == (tmp_path / "toas.toml").resolve()

    with pytest.raises(ValueError, match="usage: /config"):
        handle_config_help_commands("config", ["wat"], step_mod=step_mod, context=ctx)


def test_config_backend_validation_error_branches():
    import toas.step as step_mod

    cfg_with_backend = OperatorConfig(llm=LLMPolicy(backends=(BackendCatalogEntry(id="b1", base_url="http://x"),)))
    with pytest.raises(ValueError, match="backend field must be one of"):
        handle_config_help_commands("config", ["backend", "set", "b1.nope", "x"], step_mod=step_mod, context=_ctx(config=cfg_with_backend))
    with pytest.raises(ValueError, match="unknown backend id: missing"):
        handle_config_help_commands("config", ["backend", "set", "missing.model", "x"], step_mod=step_mod, context=_ctx(config=cfg_with_backend))
    with pytest.raises(ValueError, match="backend api_key_source must be env\\|keyring"):
        handle_config_help_commands("config", ["backend", "set", "b1.api_key_source", "bad"], step_mod=step_mod, context=_ctx(config=cfg_with_backend))


def test_config_key_validator_branch():
    class _M:
        @staticmethod
        def valid_config_keys():
            return ["a.b"]

    _validate_known_config_key("a.b", step_mod=_M)
    with pytest.raises(ValueError, match="unknown config key"):
        _validate_known_config_key("x.y", step_mod=_M)


def test_prompt_workspace_helper_env_shell_and_workspace(tmp_path, monkeypatch):
    import toas.step as step_mod

    with pytest.raises(ValueError, match="invalid env key"):
        _validate_env_key("1BAD", step_mod=step_mod)

    monkeypatch.setattr(step_mod, "normalize_shell_grants", lambda grants: tuple(grants))
    cfg = OperatorConfig()
    out = _handle_shell_config(["config", "list"], step_mod=step_mod, context=_ctx(config=cfg))
    assert "config shell grants" in out[0]["content"]
    with pytest.raises(ValueError, match="usage:"):
        _handle_shell_config(["config", "reset", "extra"], step_mod=step_mod, context=_ctx(config=cfg))

    context = _ctx(command_cwd=str(tmp_path))
    assert _resolve_workspace_arg("x", context=context) == (tmp_path / "x").resolve()


def test_extract_replay_helper_branches(monkeypatch):
    import toas.step as step_mod

    with pytest.raises(ValueError, match="no prior assistant message"):
        _latest_assistant_target([{"role": "user", "content": "u"}])

    monkeypatch.setattr(step_mod, "extract_plan_with_status", lambda _c, yaml_position="any": (None, True))
    monkeypatch.setattr(step_mod, "_extract_loose_command", lambda _c: (None, False))
    candidates = _collect_replay_candidates(step_mod=step_mod, context=_ctx(working=[{"role": "assistant", "content": "x"}, {"role": "user", "content": "/replay"}]))
    assert candidates == []

    rendered = _render_replay_candidates(
        [{"index": 1, "preview": "message #1 user: tool plan", "plan": []}],
        dry_run=False,
        context=_ctx(already_executed_indices={1}),
    )
    assert "already executed" in rendered[0]["content"]


def test_replay_queue_resume_action_unknown_id(monkeypatch):
    import toas.step as step_mod

    with pytest.raises(ValueError, match="unknown replay queue id"):
        handle_extract_replay_commands(
            "replay",
            ["--resume", "q9"],
            step_mod=step_mod,
            context=_ctx(events=[]),
        )


def test_replay_queue_block_and_approve_flow(monkeypatch):
    import toas.step as step_mod

    plan = [
        {"tool_name": "echo", "args": {"text": "ok"}},
        {"tool_name": "shell", "args": {"argv": ["blocked"]}},
        {"tool_name": "echo", "args": {"text": "tail"}},
    ]
    monkeypatch.setattr(step_mod, "extract_plan_with_status", lambda _c, yaml_position="any": (plan, False))
    monkeypatch.setattr(step_mod, "_extract_loose_command", lambda _c: (None, False))
    monkeypatch.setattr(step_mod, "_as_nodes", lambda nodes: nodes)
    monkeypatch.setattr(step_mod, "resolve_effective_env_modifiers", lambda _w: {})
    monkeypatch.setattr(step_mod, "resolve_effective_shell_allowed", lambda _w, _c: ("echo",))

    def _execute_plan(single_plan, **_kwargs):
        call = single_plan[0]
        if call["tool_name"] == "shell":
            return [
                {
                    "role": "result",
                    "content": "[ERROR] shell: tool shell disallows command: blocked",
                    "payload": {
                        "tool_name": "shell",
                        "ok": False,
                        "error": "tool shell disallows command: blocked",
                        "summary": "tool shell disallows command: blocked",
                    },
                }
            ]
        return [{"role": "result", "content": "ok", "payload": {"tool_name": call["tool_name"], "ok": True}}]

    def _execute_plan_user_context(single_plan, **_kwargs):
        call = single_plan[0]
        return [{"role": "result", "content": "approved", "payload": {"tool_name": call["tool_name"], "ok": True}}]

    monkeypatch.setattr(step_mod, "_execute_plan", _execute_plan)
    monkeypatch.setattr(step_mod, "_execute_plan_user_context", _execute_plan_user_context)

    working = [{"role": "assistant", "content": "```yaml\n- tool_name: echo\n```"}, {"role": "user", "content": "/replay --index 1"}]
    out = handle_extract_replay_commands(
        "replay",
        ["--index", "1"],
        step_mod=step_mod,
        context=_ctx(working=working, execute=lambda _w, _p: []),
    )
    blocked_updates = [node["queue_update"] for node in out if isinstance(node, dict) and isinstance(node.get("queue_update"), dict)]
    assert blocked_updates
    blocked = blocked_updates[-1]
    assert blocked["id"] == "q1"
    assert blocked["status"] == "blocked"
    assert blocked["next_index"] == 1

    out2 = handle_extract_replay_commands(
        "replay",
        ["--approve", "q1"],
        step_mod=step_mod,
        context=_ctx(
            working=[{"role": "user", "content": "/replay --approve q1"}],
            events=[{"kind": "execution_queue", "payload": blocked}],
        ),
    )
    approved_updates = [node["queue_update"] for node in out2 if isinstance(node, dict) and isinstance(node.get("queue_update"), dict)]
    assert approved_updates
    assert approved_updates[-1]["status"] == "completed"


def test_replay_queue_skip_and_resume_flow(monkeypatch):
    import toas.step as step_mod

    plan = [
        {"tool_name": "echo", "args": {"text": "head"}},
        {"tool_name": "shell", "args": {"argv": ["blocked"]}},
        {"tool_name": "echo", "args": {"text": "tail"}},
    ]
    monkeypatch.setattr(step_mod, "extract_plan_with_status", lambda _c, yaml_position="any": (plan, False))
    monkeypatch.setattr(step_mod, "_extract_loose_command", lambda _c: (None, False))
    monkeypatch.setattr(step_mod, "_as_nodes", lambda nodes: nodes)
    monkeypatch.setattr(step_mod, "resolve_effective_env_modifiers", lambda _w: {})
    monkeypatch.setattr(step_mod, "resolve_effective_shell_allowed", lambda _w, _c: ("echo",))

    def _execute_plan(single_plan, **_kwargs):
        call = single_plan[0]
        if call["tool_name"] == "shell":
            return [
                {
                    "role": "result",
                    "content": "[ERROR] shell: tool shell disallows command: blocked",
                    "payload": {
                        "tool_name": "shell",
                        "ok": False,
                        "error": "tool shell disallows command: blocked",
                        "summary": "tool shell disallows command: blocked",
                    },
                }
            ]
        return [{"role": "result", "content": "ok", "payload": {"tool_name": call["tool_name"], "ok": True}}]

    monkeypatch.setattr(step_mod, "_execute_plan", _execute_plan)
    monkeypatch.setattr(step_mod, "_execute_plan_user_context", lambda single_plan, **_kwargs: single_plan)

    out = handle_extract_replay_commands(
        "replay",
        ["--index", "1"],
        step_mod=step_mod,
        context=_ctx(
            working=[{"role": "assistant", "content": "```yaml\n- tool_name: echo\n```"}, {"role": "user", "content": "/replay --index 1"}],
            execute=lambda _w, _p: [],
        ),
    )
    blocked = [node["queue_update"] for node in out if isinstance(node, dict) and isinstance(node.get("queue_update"), dict)][-1]
    assert blocked["status"] == "blocked"
    assert blocked["next_index"] == 1

    out2 = handle_extract_replay_commands(
        "replay",
        ["--skip", "q1"],
        step_mod=step_mod,
        context=_ctx(
            working=[{"role": "user", "content": "/replay --skip q1"}],
            events=[{"kind": "execution_queue", "payload": blocked}],
        ),
    )
    updates = [node["queue_update"] for node in out2 if isinstance(node, dict) and isinstance(node.get("queue_update"), dict)]
    assert updates
    assert updates[-1]["status"] == "completed"
    assert any(entry["status"] == "skipped" and entry["index"] == 1 for entry in updates[-1]["entries"])
    assert any(entry["status"] == "ran" and entry["index"] == 2 for entry in updates[-1]["entries"])


def test_replay_queue_cancel_marks_remaining_and_is_terminal(monkeypatch):
    import toas.step as step_mod

    queue = {
        "id": "q3",
        "status": "blocked",
        "next_index": 1,
        "target_message_index": 2,
        "plan": [
            {"tool_name": "echo", "args": {"text": "head"}},
            {"tool_name": "shell", "args": {"argv": ["blocked"]}},
            {"tool_name": "echo", "args": {"text": "tail"}},
        ],
        "entries": [{"index": 0, "tool_name": "echo", "status": "ran"}],
    }
    monkeypatch.setattr(step_mod, "_as_nodes", lambda nodes: nodes)

    out = handle_extract_replay_commands(
        "replay",
        ["--cancel", "q3"],
        step_mod=step_mod,
        context=_ctx(
            working=[{"role": "user", "content": "/replay --cancel q3"}],
            events=[{"kind": "execution_queue", "payload": queue}],
        ),
    )
    updates = [node["queue_update"] for node in out if isinstance(node, dict) and isinstance(node.get("queue_update"), dict)]
    assert updates
    cancelled = updates[-1]
    assert cancelled["status"] == "cancelled"
    assert cancelled["next_index"] == 3
    assert sum(1 for entry in cancelled["entries"] if entry["status"] == "cancelled") == 2

    out2 = handle_extract_replay_commands(
        "replay",
        ["--resume", "q3"],
        step_mod=step_mod,
        context=_ctx(
            working=[{"role": "user", "content": "/replay --resume q3"}],
            events=[{"kind": "execution_queue", "payload": cancelled}],
        ),
    )
    assert "already terminal" in out2[0]["content"]
