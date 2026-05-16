from toas.llm import NO_THINKING, Settings
from toas.llm_harness import (
    HOSTILE_TOOL_SYSTEM,
    PROVIDER_PROTOCOL_MARKER,
    analyze_chat_response,
    compare_thinking_modes,
    evaluate_expectations,
    main,
    probe_chat,
    run_harness,
)


def test_helper_dedupe_and_role_execution_claim_detection():
    from toas.llm_harness import _dedupe_keep_order, _role_execution_claim_present

    assert _dedupe_keep_order(["F1", "F2", "F1", "F3"]) == ["F1", "F2", "F3"]
    assert _role_execution_claim_present("I executed the command") is True
    assert _role_execution_claim_present("I suggest running this command") is False


def test_analyze_chat_response_tracks_reasoning_and_exact_match():
    body = {
        "model": "local-model",
        "choices": [
            {
                "finish_reason": "stop",
                "message": {
                    "content": "OK",
                    "reasoning_content": "lots of hidden reasoning",
                },
            }
        ],
        "usage": {"total_tokens": 10},
        "timings": {"predicted_ms": 100},
    }

    assert analyze_chat_response(body, expected="OK") == {
        "model": "local-model",
        "finish_reason": "stop",
        "content": "OK",
        "has_reasoning_content": True,
        "reasoning_chars": 24,
        "usage": {"total_tokens": 10},
        "timings": {"predicted_ms": 100},
        "starts_with_yaml_fence": False,
        "starts_with_json_object": False,
        "leading_text_present": True,
        "expected": "OK",
        "exact_match": True,
    }


def test_analyze_chat_response_checks_json_and_yaml_expectations():
    json_body = {
        "model": "local-model",
        "choices": [{"finish_reason": "stop", "message": {"content": '{"ok": true}'}}],
    }
    yaml_body = {
        "model": "local-model",
        "choices": [{"finish_reason": "stop", "message": {"content": "```yaml\n- tool_name: echo\n```"}}],
    }

    json_report = analyze_chat_response(json_body, expect_json=True)
    yaml_report = analyze_chat_response(yaml_body, expect_yaml=True)

    assert json_report["json_parseable"] is True
    assert json_report["json"] == {"ok": True}
    assert yaml_report["yaml_fence_present"] is True


def test_analyze_chat_response_tracks_structure_and_provider_marker():
    body = {
        "model": "local-model",
        "choices": [{"finish_reason": "stop", "message": {"content": 'TOOL_CALL: {"name":"echo"}'}}],
    }

    report = analyze_chat_response(body, provider_marker=PROVIDER_PROTOCOL_MARKER)

    assert report["provider_protocol_marker_present"] is True
    assert report["leading_text_present"] is True
    assert report["starts_with_yaml_fence"] is False
    assert report["starts_with_json_object"] is False


def test_probe_chat_returns_structured_error_for_transport_failure(monkeypatch):
    import toas.llm_harness as harness

    def fake_request_json(*_args, **_kwargs):
        raise TimeoutError("timed out")

    monkeypatch.setattr(harness, "_request_json", fake_request_json)

    report = probe_chat(Settings(), label="hello", prompt="hello", extra_body=NO_THINKING)

    assert report["label"] == "hello"
    assert report["thinking_disabled"] is True
    assert report["error"] == "timed out"
    assert report["error_type"] == "TimeoutError"
    assert report["expectation_report"]["failure_mode_ids"] == ["F5"]
    assert isinstance(report["elapsed_ms"], int)


def test_probe_chat_requires_prompt_or_messages():
    import toas.llm_harness as harness

    report = harness.probe_chat(Settings(), label="missing")
    assert report["error_type"] == "ValueError"
    assert "requires prompt or messages" in report["error"]


def test_probe_chat_uses_messages_directly(monkeypatch):
    seen = {}

    def fake_request_json(_url, *, payload=None, timeout_s=15):
        seen["payload"] = payload
        return {"choices": [{"finish_reason": "stop", "message": {"content": "OK"}}]}

    import toas.llm_harness as harness

    monkeypatch.setattr(harness, "_request_json", fake_request_json)
    report = harness.probe_chat(
        Settings(),
        messages=[{"role": "system", "content": "s"}, {"role": "user", "content": "u"}],
    )
    assert seen["payload"]["messages"][0]["role"] == "system"
    assert report["content"] == "OK"


def test_compare_thinking_modes_probes_both_request_shapes(monkeypatch):
    seen = []

    def fake_request_json(_url, *, payload=None, timeout_s=15):
        seen.append(payload)
        return {"choices": [{"finish_reason": "stop", "message": {"content": "OK"}}]}

    import toas.llm_harness as harness

    monkeypatch.setattr(harness, "_request_json", fake_request_json)

    report = compare_thinking_modes(Settings(), label="exact_ok", prompt="Reply with exactly OK.")

    assert list(report) == ["thinking_on", "thinking_off"]
    assert "chat_template_kwargs" not in seen[0]
    assert seen[1]["chat_template_kwargs"] == NO_THINKING["chat_template_kwargs"]
    assert report["thinking_off"]["thinking_disabled"] is True
    assert report["thinking_on"]["thinking_disabled"] is False
    assert report["thinking_on"]["expectation_report"]["pass"] is True


def test_run_harness_protocol_set_includes_hostile_system_probes(monkeypatch):
    import toas.llm_harness as harness

    def fake_request_json(_url, *, payload=None, timeout_s=15):
        return {"model": "local-model", "choices": [{"finish_reason": "stop", "message": {"content": "```yaml\nok: true\n```"}}]}

    monkeypatch.setattr(harness, "_request_json", fake_request_json)

    report = run_harness(Settings(), timeout_s=7, scenario_set="protocol")

    assert "scenarios" not in report
    assert report["protocol_collision"]["hostile_system"] == HOSTILE_TOOL_SYSTEM
    assert "yaml_tool_call_word" in report["protocol_collision"]["scenarios"]
    assert report["protocol_collision"]["scenarios"]["yaml_tool_call_word"]["thinking_disabled"] is True
    assert "taxonomy" in report
    assert "provider_collision" in report["taxonomy"]["packs"]


def test_evaluate_expectations_reports_failure_modes_and_remediation():
    report = {
        "exact_match": False,
        "provider_protocol_marker_present": True,
    }
    result = evaluate_expectations(
        report,
        expectations={
            "exact_match": True,
            "provider_protocol_marker_present": False,
        },
    )
    assert result["pass"] is False
    assert result["failure_mode_ids"] == ["F1", "F2"]
    assert len(result["recommended_remediation"]) == 2


def test_main_can_write_report_to_output_file(monkeypatch, tmp_path, capsys):
    import toas.llm_harness as harness

    monkeypatch.setattr(
        harness,
        "run_harness",
        lambda settings, timeout_s=15, scenario_set="all": {"ok": True, "timeout_s": timeout_s, "scenario_set": scenario_set},
    )
    monkeypatch.setattr(
        harness.Settings,
        "from_env",
        classmethod(lambda cls: Settings()),
    )
    out = tmp_path / "report.json"
    monkeypatch.setattr("sys.argv", ["toas-llm-harness", "--timeout-s", "9", "--scenario-set", "protocol", "--output", str(out)])

    main()

    rendered = capsys.readouterr().out
    assert '"ok": true' in rendered
    assert out.read_text(encoding="utf-8") == rendered


def test_main_applies_base_url_and_model_overrides(monkeypatch, capsys):
    import toas.llm_harness as harness

    captured = {}

    def fake_run(settings, timeout_s=15, scenario_set="all"):
        captured["settings"] = settings
        captured["timeout_s"] = timeout_s
        captured["scenario_set"] = scenario_set
        return {"ok": True}

    monkeypatch.setattr(harness, "run_harness", fake_run)
    monkeypatch.setattr(harness.Settings, "from_env", classmethod(lambda cls: Settings()))
    monkeypatch.setattr(
        "sys.argv",
        [
            "toas-llm-harness",
            "--base-url",
            "http://localhost:8000/v1",
            "--api-key",
            "k1",
            "--model",
            "m1",
            "--timeout-s",
            "5",
        ],
    )
    main()
    _ = capsys.readouterr()
    settings = captured["settings"]
    assert settings.llm_base_url == "http://localhost:8000/v1"
    assert settings.llm_api_key == "k1"
    assert settings.llm_model == "m1"
    assert captured["timeout_s"] == 5


def test_main_applies_model_or_key_override_without_base_url(monkeypatch, capsys):
    import toas.llm_harness as harness

    captured = {}

    def fake_run(settings, timeout_s=15, scenario_set="all"):
        captured["settings"] = settings
        return {"ok": True}

    monkeypatch.setattr(harness, "run_harness", fake_run)
    monkeypatch.setattr(harness.Settings, "from_env", classmethod(lambda cls: Settings(llm_base_url="http://x/v1", llm_api_key="k0", llm_model="m0")))
    monkeypatch.setattr("sys.argv", ["toas-llm-harness", "--model", "m2"])
    main()
    _ = capsys.readouterr()
    assert captured["settings"].llm_base_url == "http://x/v1"
    assert captured["settings"].llm_model == "m2"
