from __future__ import annotations

from toas.runtime.executable_fence_lanes import (
    extract_bash_exec_plans,
    extract_json_exec_plans,
    parse_bash_exec_fence,
    parse_json_exec_fence,
    parse_python_exec_fence,
)
from toas.runtime.markdown_fence import scan_markdown_fences


def test_parse_bash_exec_fence_maps_prompted_lines_to_one_shell_script():
    fence = scan_markdown_fences("```bash exec\n$ echo one\n$ echo two\n```")[0]

    assert parse_bash_exec_fence(fence) == [
        {"tool_name": "shell_script", "args": {"script": "echo one\necho two"}}
    ]


def test_parse_bash_exec_fence_preserves_unprompted_multiline_body():
    fence = scan_markdown_fences("```sh exec\nset -e\necho $HOME\n```")[0]

    assert parse_bash_exec_fence(fence) == [
        {"tool_name": "shell_script", "args": {"script": "set -e\necho $HOME"}}
    ]


def test_parse_bash_exec_fence_rejects_inactive_or_non_bash_fences():
    inert = scan_markdown_fences("```bash\necho hi\n```")[0]
    python = scan_markdown_fences("```python exec\nprint('hi')\n```")[0]

    assert parse_bash_exec_fence(inert) is None
    assert parse_bash_exec_fence(python) is None


def test_extract_bash_exec_plans_returns_source_positions_and_skips_empty_bodies():
    content = "```bash exec\n\n```\ntext\n```bash exec\necho hi\n```"

    plans = extract_bash_exec_plans(content)

    assert len(plans) == 1
    assert plans[0][0][0]["args"]["script"] == "echo hi"
    assert plans[0][1] == content.index("```bash exec", 1)


def test_json_exec_fence_normalizes_like_equivalent_yaml():
    fence = scan_markdown_fences('```json exec\n{"tool_name":"echo","args":{"text":"hi"}}\n```')[0]

    assert parse_json_exec_fence(fence) == [{"tool_name": "echo", "args": {"text": "hi"}}]


def test_json_exec_fence_rejects_duplicate_keys_and_inert_json():
    duplicate = scan_markdown_fences('```json exec\n{"tool_name":"echo","tool_name":"shell"}\n```')[0]
    inert = scan_markdown_fences('```json\n{"tool_name":"echo","args":{"text":"hi"}}\n```')[0]

    assert parse_json_exec_fence(duplicate) is None
    assert parse_json_exec_fence(inert) is None


def test_extract_json_exec_plans_returns_source_position():
    content = 'prefix\n```json exec\n{"tool_name":"echo","args":{"text":"hi"}}\n```'

    plans = extract_json_exec_plans(content)

    assert plans[0][0] == [{"tool_name": "echo", "args": {"text": "hi"}}]
    assert plans[0][1] == content.index("```json exec")


def test_parse_python_exec_fence_carries_runtime_and_cwd_arguments():
    fence = scan_markdown_fences(
        '```python exec runtime="uv run python" cwd="scripts"\nprint("hi")\n```'
    )[0]

    assert parse_python_exec_fence(fence) == [
        {
            "tool_name": "python_script",
            "args": {
                "script": 'print("hi")',
                "runtime": ["uv", "run", "python"],
                "cwd": "scripts",
            },
        }
    ]
