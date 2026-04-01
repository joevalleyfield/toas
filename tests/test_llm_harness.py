from toas.llm import Settings
from toas.llm_harness import analyze_chat_response, probe_chat


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


def test_probe_chat_returns_structured_error_for_transport_failure(monkeypatch):
    import toas.llm_harness as harness

    def fake_request_json(*_args, **_kwargs):
        raise TimeoutError("timed out")

    monkeypatch.setattr(harness, "_request_json", fake_request_json)

    report = probe_chat(Settings(), prompt="hello")

    assert report == {
        "error": "timed out",
        "error_type": "TimeoutError",
    }
