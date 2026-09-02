from __future__ import annotations

from toas.runtime.executable_fence_lanes import (
    extract_bash_exec_plans,
    extract_json_exec_plans,
    json_exec_fence_toolset,
    parse_bash_exec_fence,
    parse_interpreter_exec_fence,
    parse_json_exec_fence,
    parse_powershell_exec_fence,
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


def test_parse_bash_exec_fence_carries_timeout_attribute():
    fence = scan_markdown_fences("```bash exec timeout_s=30\necho hi\n```")[0]

    assert parse_bash_exec_fence(fence) == [
        {"tool_name": "shell_script", "args": {"script": "echo hi", "timeout_s": 30}}
    ]


def test_parse_bash_exec_fence_rejects_inactive_or_non_bash_fences():
    inert = scan_markdown_fences("```bash\necho hi\n```")[0]
    python = scan_markdown_fences("```python exec\nprint('hi')\n```")[0]

    assert parse_bash_exec_fence(inert) is None
    assert parse_bash_exec_fence(python) is None


def test_parse_bash_exec_fence_rejects_empty_script():
    fence = scan_markdown_fences("```bash exec\n   \n```\n")[0]

    assert parse_bash_exec_fence(fence) is None


def test_parse_bash_exec_fence_rejects_prompted_blank_script():
    fence = scan_markdown_fences("```bash exec\n$ \n```\n")[0]

    assert parse_bash_exec_fence(fence) is None


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


def test_parse_json_exec_fence_rejects_malformed_json():
    fence = scan_markdown_fences("```json exec\n{bad\n```\n")[0]

    assert parse_json_exec_fence(fence) is None


def test_json_exec_fence_toolset_only_applies_to_active_json():
    active = scan_markdown_fences("```json exec\n{}\n```")[0]
    inert = scan_markdown_fences("```json\n{}\n```")[0]

    assert json_exec_fence_toolset(active) == "toas"
    assert json_exec_fence_toolset(inert) is None


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


def test_parse_python_exec_fence_carries_timeout_attribute():
    fence = scan_markdown_fences("```python exec timeout_s=30\nprint('hi')\n```")[0]

    assert parse_python_exec_fence(fence) == [
        {"tool_name": "python_script", "args": {"script": "print('hi')", "timeout_s": 30}}
    ]


def test_other_script_fences_carry_timeout_attribute():
    powershell = scan_markdown_fences("```powershell exec timeout_s=30\nWrite-Host hi\n```")[0]
    interpreter = scan_markdown_fences("```sql exec runtime=sqlite3 timeout_s=30\nselect 1;\n```")[0]

    assert parse_powershell_exec_fence(powershell) == [
        {"tool_name": "powershell_script", "args": {"script": "Write-Host hi", "timeout_s": 30}}
    ]
    assert parse_interpreter_exec_fence(interpreter) == [
        {
            "tool_name": "interpreter_script",
            "args": {"language": "sql", "script": "select 1;", "runtime": ["sqlite3"], "timeout_s": 30},
        }
    ]


def test_script_fences_reject_nonpositive_timeout_attribute():
    bash = scan_markdown_fences("```bash exec timeout_s=0\necho hi\n```")[0]
    python = scan_markdown_fences("```python exec timeout_s=nope\nprint(1)\n```")[0]
    powershell = scan_markdown_fences("```powershell exec timeout_s=0\nWrite-Host hi\n```")[0]
    interpreter = scan_markdown_fences("```sql exec runtime=sqlite3 timeout_s=nope\nselect 1;\n```")[0]

    assert parse_bash_exec_fence(bash) is None
    assert parse_python_exec_fence(python) is None
    assert parse_powershell_exec_fence(powershell) is None
    assert parse_interpreter_exec_fence(interpreter) is None


def test_parse_python_exec_fence_rejects_empty_or_invalid_boolean_attributes():
    empty = scan_markdown_fences("```python exec\n\n```")[0]
    invalid = scan_markdown_fences("```python exec persist=maybe\nprint(1)\n```")[0]

    assert parse_python_exec_fence(empty) is None
    assert parse_python_exec_fence(invalid) is None


def test_parse_python_exec_fence_accepts_false_boolean_attributes():
    fence = scan_markdown_fences(
        "```python exec persist=false overwrite=false\nprint(1)\n```"
    )[0]

    assert parse_python_exec_fence(fence) == [
        {
            "tool_name": "python_script",
            "args": {"script": "print(1)", "persist": False, "overwrite": False},
        }
    ]


def test_parse_powershell_exec_fence_maps_script_and_attributes():
    fence = scan_markdown_fences(
        '```powershell exec cwd="scripts" path="hello###.ps1" persist=false\nWrite-Output "hi"\n```'
    )[0]

    assert parse_powershell_exec_fence(fence) == [
        {
            "tool_name": "powershell_script",
            "args": {
                "script": 'Write-Output "hi"',
                "cwd": "scripts",
                "path": "hello###.ps1",
                "persist": False,
            },
        }
    ]


def test_parse_powershell_exec_fence_accepts_runtime_and_rejects_empty_or_invalid():
    runtime = scan_markdown_fences(
        '```powershell exec runtime="pwsh -NoProfile"\nWrite-Output "hi"\n```'
    )[0]
    empty = scan_markdown_fences("```powershell exec\n\n```")[0]
    invalid = scan_markdown_fences("```powershell exec persist=maybe\nWrite-Output hi\n```")[0]

    assert parse_powershell_exec_fence(runtime)[0]["args"]["runtime"] == ["pwsh", "-NoProfile"]
    assert parse_powershell_exec_fence(empty) is None
    assert parse_powershell_exec_fence(invalid) is None


def test_parse_interpreter_exec_fence_requires_explicit_runtime_for_bc():
    active = scan_markdown_fences("```bc exec runtime=bc\nscale=4\n1 / 3\n```")[0]
    unsupported = scan_markdown_fences("```bc exec\n1 / 3\n```")[0]

    assert parse_interpreter_exec_fence(active) == [
        {
            "tool_name": "interpreter_script",
            "args": {"language": "bc", "script": "scale=4\n1 / 3", "runtime": ["bc"]},
        }
    ]
    assert parse_interpreter_exec_fence(unsupported) is None


def test_parse_interpreter_exec_fence_carries_artifact_attributes_and_rejects_bad_forms():
    fence = scan_markdown_fences(
        "```bc exec runtime=bc cwd=math path=calc.bc persist=true overwrite=false\n1 / 3\n```"
    )[0]
    empty = scan_markdown_fences("```bc exec runtime=bc\n\n```")[0]
    no_runtime = scan_markdown_fences("```bc exec cwd=math\n1 / 3\n```")[0]
    invalid = scan_markdown_fences("```bc exec runtime=bc persist=maybe\n1 / 3\n```")[0]

    assert parse_interpreter_exec_fence(fence)[0]["args"] == {
        "language": "bc",
        "script": "1 / 3",
        "runtime": ["bc"],
        "cwd": "math",
        "path": "calc.bc",
        "persist": True,
        "overwrite": False,
    }
    assert parse_interpreter_exec_fence(empty) is None
    assert parse_interpreter_exec_fence(no_runtime) is None
    assert parse_interpreter_exec_fence(invalid) is None
