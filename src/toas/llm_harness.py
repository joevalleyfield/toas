import argparse
import json
from time import monotonic
from urllib import request

from .llm import NO_THINKING, Settings


def _request_json(url: str, *, payload: dict | None = None, timeout_s: int = 15):
    data = None
    method = "GET"
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        method = "POST"
        headers["Content-Type"] = "application/json"

    req = request.Request(url, data=data, headers=headers, method=method)
    with request.urlopen(req, timeout=timeout_s) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_health(settings: Settings, *, timeout_s: int = 15) -> dict:
    base = settings.llm_base_url.removesuffix("/v1")
    return _request_json(f"{base}/health", timeout_s=timeout_s)


def fetch_models(settings: Settings, *, timeout_s: int = 15) -> dict:
    return _request_json(f"{settings.llm_base_url.rstrip('/')}/models", timeout_s=timeout_s)


def analyze_chat_response(
    body: dict,
    *,
    expected: str | None = None,
    expect_json: bool = False,
    expect_yaml: bool = False,
) -> dict:
    message = body["choices"][0]["message"]
    content = message.get("content", "")
    reasoning = message.get("reasoning_content")

    report = {
        "model": body.get("model"),
        "finish_reason": body["choices"][0].get("finish_reason"),
        "content": content,
        "has_reasoning_content": bool(reasoning),
        "reasoning_chars": len(reasoning or ""),
        "usage": body.get("usage"),
        "timings": body.get("timings"),
    }

    if expected is not None:
        report["expected"] = expected
        report["exact_match"] = content == expected
    if expect_json:
        try:
            report["json"] = json.loads(content)
            report["json_parseable"] = True
        except json.JSONDecodeError:
            report["json_parseable"] = False
    if expect_yaml:
        report["yaml_fence_present"] = "```yaml" in content and "```" in content

    return report


def probe_chat(
    settings: Settings,
    *,
    label: str | None = None,
    prompt: str,
    expected: str | None = None,
    expect_json: bool = False,
    expect_yaml: bool = False,
    extra_body: dict | None = None,
    timeout_s: int = 15,
) -> dict:
    started = monotonic()
    try:
        payload = {
            "model": settings.llm_model,
            "messages": [{"role": "user", "content": prompt}],
        }
        if extra_body is not None:
            payload.update(extra_body)

        body = _request_json(
            f"{settings.llm_base_url.rstrip('/')}/chat/completions",
            payload=payload,
            timeout_s=timeout_s,
        )
    except Exception as exc:
        return {
            "label": label,
            "prompt": prompt,
            "thinking_disabled": extra_body == NO_THINKING,
            "elapsed_ms": int((monotonic() - started) * 1000),
            "error": str(exc),
            "error_type": type(exc).__name__,
        }

    report = analyze_chat_response(
        body,
        expected=expected,
        expect_json=expect_json,
        expect_yaml=expect_yaml,
    )
    report["label"] = label
    report["prompt"] = prompt
    report["thinking_disabled"] = extra_body == NO_THINKING
    report["elapsed_ms"] = int((monotonic() - started) * 1000)
    return report


def compare_thinking_modes(
    settings: Settings,
    *,
    label: str,
    prompt: str,
    expected: str | None = None,
    expect_json: bool = False,
    expect_yaml: bool = False,
    timeout_s: int = 15,
) -> dict:
    return {
        "thinking_on": probe_chat(
            settings,
            label=f"{label}_thinking_on",
            prompt=prompt,
            expected=expected,
            expect_json=expect_json,
            expect_yaml=expect_yaml,
            timeout_s=timeout_s,
        ),
        "thinking_off": probe_chat(
            settings,
            label=f"{label}_thinking_off",
            prompt=prompt,
            expected=expected,
            expect_json=expect_json,
            expect_yaml=expect_yaml,
            extra_body=NO_THINKING,
            timeout_s=timeout_s,
        ),
    }


def run_harness(settings: Settings, *, timeout_s: int = 15) -> dict:
    return {
        "base_url": settings.llm_base_url,
        "requested_model": settings.llm_model,
        "timeout_s": timeout_s,
        "health": fetch_health(settings, timeout_s=timeout_s),
        "models": fetch_models(settings, timeout_s=timeout_s),
        "scenarios": {
            "exact_ok": compare_thinking_modes(
                settings,
                label="exact_ok",
                prompt="Reply with exactly OK.",
                expected="OK",
                timeout_s=timeout_s,
            ),
            "json_exact": compare_thinking_modes(
                settings,
                label="json_exact",
                prompt='Reply with exactly {"ok":true}.',
                expected='{"ok":true}',
                expect_json=True,
                timeout_s=timeout_s,
            ),
            "yaml_block": compare_thinking_modes(
                settings,
                label="yaml_block",
                prompt="Return only a fenced yaml block containing one tool call for echo with text set to hi.",
                expect_yaml=True,
                timeout_s=timeout_s,
            ),
            "json_tool_call": compare_thinking_modes(
                settings,
                label="json_tool_call",
                prompt='Return only JSON with the shape {"tool_name":"echo","text":"hi"}.',
                expect_json=True,
                timeout_s=timeout_s,
            ),
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--timeout-s", type=int, default=15)
    args = parser.parse_args()

    settings = Settings.from_env()
    if args.base_url is not None:
        settings = Settings(
            llm_base_url=args.base_url,
            llm_api_key=args.api_key or settings.llm_api_key,
            llm_model=args.model or settings.llm_model,
        )
    elif args.model is not None or args.api_key is not None:
        settings = Settings(
            llm_base_url=settings.llm_base_url,
            llm_api_key=args.api_key or settings.llm_api_key,
            llm_model=args.model or settings.llm_model,
        )

    print(json.dumps(run_harness(settings, timeout_s=args.timeout_s), indent=2, ensure_ascii=False))
