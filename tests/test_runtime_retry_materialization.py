from toas.runtime import retry_materialization
from toas.runtime.markdown_fence import FenceAttribute
from toas.runtime.retry_materialization import materialize_executable_fence_timeout


def test_fence_timeout_materialization_appends_only_to_opening_header():
    source = '```python exec runtime="uv run python"\r\nprint("hello")\r\n```\r\n'

    result = materialize_executable_fence_timeout(content=source, opening_offset=0, timeout_s=30)

    assert result.reason is None
    assert result.content == '```python exec runtime="uv run python" timeout_s=30\r\nprint("hello")\r\n```\r\n'


def test_fence_timeout_materialization_replaces_only_existing_value_and_keeps_quotes():
    source = "```python exec timeout_s='5' runtime=python\nprint('hello')\n```"

    result = materialize_executable_fence_timeout(content=source, opening_offset=0, timeout_s=30)

    assert result.content == "```python exec timeout_s='30' runtime=python\nprint('hello')\n```"


def test_fence_timeout_materialization_refuses_malformed_or_nonexecutable_headers():
    malformed = "```python exec timeout_s=5 timeout_s=6\nprint(1)\n```"
    inert = "```python\nprint(1)\n```"
    json = '```json exec\n{"tool_name":"echo","args":{"text":"hi"}}\n```'

    assert materialize_executable_fence_timeout(content=malformed, opening_offset=0, timeout_s=30).content is None
    assert materialize_executable_fence_timeout(content=inert, opening_offset=0, timeout_s=30).content is None
    assert materialize_executable_fence_timeout(content=json, opening_offset=0, timeout_s=30).content is None


def test_fence_timeout_materialization_refuses_invalid_timeout_and_missing_fence():
    source = "```python exec\nprint(1)\n```"

    assert materialize_executable_fence_timeout(content=source, opening_offset=0, timeout_s=0).content is None
    assert materialize_executable_fence_timeout(content=source, opening_offset=1, timeout_s=30).content is None


def test_fence_timeout_materialization_refuses_unpatchable_attribute_shapes(monkeypatch):
    source = "```python exec\nprint(1)\n```"

    monkeypatch.setattr(retry_materialization, "fence_attributes", lambda _fence: None)
    assert materialize_executable_fence_timeout(content=source, opening_offset=0, timeout_s=30).content is None

    monkeypatch.setattr(
        retry_materialization,
        "fence_attributes",
        lambda _fence: (
            FenceAttribute("timeout_s", "5", 20, 21, None),
            FenceAttribute("timeout_s", "6", 30, 31, None),
        ),
    )
    assert materialize_executable_fence_timeout(content=source, opening_offset=0, timeout_s=30).content is None


def test_fence_timeout_materialization_refuses_when_validation_loses_the_fence(monkeypatch):
    source = "```python exec\nprint(1)\n```"
    real_scan = retry_materialization.scan_markdown_fences

    monkeypatch.setattr(
        retry_materialization,
        "scan_markdown_fences",
        lambda value: real_scan(value) if "timeout_s=" not in value else [],
    )

    assert materialize_executable_fence_timeout(content=source, opening_offset=0, timeout_s=30).content is None
