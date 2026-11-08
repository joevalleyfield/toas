from __future__ import annotations

from pathlib import Path

from toas.runtime.executable_fence_lanes import (
    extract_bash_exec_plans,
    extract_interpreter_exec_plans,
    extract_json_exec_plans,
    extract_powershell_exec_plans,
    extract_python_exec_plans,
    extract_write_fence_plans,
    json_exec_fence_toolset,
    parse_bash_exec_fence,
    parse_interpreter_exec_fence,
    parse_json_exec_fence,
    parse_powershell_exec_fence,
    parse_python_exec_fence,
    parse_write_fence,
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
    duplicate = scan_markdown_fences('```json exec\n{"tool_name":"echo","tool_name":"shell"}\n```')[
        0
    ]
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
    interpreter = scan_markdown_fences("```sql exec runtime=sqlite3 timeout_s=30\nselect 1;\n```")[
        0
    ]

    assert parse_powershell_exec_fence(powershell) == [
        {"tool_name": "powershell_script", "args": {"script": "Write-Host hi", "timeout_s": 30}}
    ]
    assert parse_interpreter_exec_fence(interpreter) == [
        {
            "tool_name": "interpreter_script",
            "args": {
                "language": "sql",
                "script": "select 1;",
                "runtime": ["sqlite3"],
                "timeout_s": 30,
            },
        }
    ]


def test_script_fences_reject_nonpositive_timeout_attribute():
    bash = scan_markdown_fences("```bash exec timeout_s=0\necho hi\n```")[0]
    python = scan_markdown_fences("```python exec timeout_s=nope\nprint(1)\n```")[0]
    powershell = scan_markdown_fences("```powershell exec timeout_s=0\nWrite-Host hi\n```")[0]
    interpreter = scan_markdown_fences(
        "```sql exec runtime=sqlite3 timeout_s=nope\nselect 1;\n```"
    )[0]

    assert parse_bash_exec_fence(bash) is None
    assert parse_python_exec_fence(python) is None
    assert parse_powershell_exec_fence(powershell) is None
    assert parse_interpreter_exec_fence(interpreter) is None


def test_parse_python_exec_fence_rejects_empty_or_invalid_boolean_attributes():
    empty = scan_markdown_fences("```python exec\n\n```")[0]
    invalid = scan_markdown_fences("```python exec persist=maybe\nprint(1)\n```")[0]
    inert = scan_markdown_fences("```python\nprint(1)\n```")[0]
    write_fence = scan_markdown_fences("```python write path=foo.py\nprint(1)\n```")[0]

    assert parse_python_exec_fence(empty) is None
    assert parse_python_exec_fence(invalid) is None
    assert parse_python_exec_fence(inert) is None
    assert parse_python_exec_fence(write_fence) is None


def test_parse_python_exec_fence_accepts_false_boolean_attributes():
    fence = scan_markdown_fences("```python exec persist=false overwrite=false\nprint(1)\n```")[0]

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
    inert = scan_markdown_fences("```powershell\nWrite-Output hi\n```")[0]
    write_fence = scan_markdown_fences("```powershell write path=run.ps1\nWrite-Output hi\n```")[0]

    assert parse_powershell_exec_fence(runtime)[0]["args"]["runtime"] == ["pwsh", "-NoProfile"]
    assert parse_powershell_exec_fence(empty) is None
    assert parse_powershell_exec_fence(invalid) is None
    assert parse_powershell_exec_fence(inert) is None
    assert parse_powershell_exec_fence(write_fence) is None


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


def test_resolve_fence_script_ref_and_error_handling(tmp_path, monkeypatch):
    from pathlib import Path

    from toas.runtime.executable_fence_lanes import _resolve_fence_script_ref

    monkeypatch.chdir(tmp_path)
    # direct file
    script_file = tmp_path / "hello.py"
    script_file.write_text("print('hello')", encoding="utf-8")
    assert _resolve_fence_script_ref("hello.py") == "print('hello')"

    # scratch file
    scratch_dir = tmp_path / ".toas" / "scratch"
    scratch_dir.mkdir(parents=True)
    scratch_file = scratch_dir / "ib_abc123.txt"
    scratch_file.write_text("echo scratch", encoding="utf-8")
    assert _resolve_fence_script_ref("ib_abc123") == "echo scratch"

    # missing file
    assert _resolve_fence_script_ref("nonexistent") is None

    # OSError during read
    def raise_os_error(*args, **kwargs):
        raise OSError("read failure")

    monkeypatch.setattr(Path, "read_text", raise_os_error)
    assert _resolve_fence_script_ref("hello.py") is None


def test_parse_bash_exec_fence_handles_runtime_error_and_ref(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    sh_file = tmp_path / "script.sh"
    sh_file.write_text("echo from_file", encoding="utf-8")

    # ref resolution on empty body
    fence_ref = scan_markdown_fences("```bash exec ref=script.sh\n\n```")[0]
    plan = parse_bash_exec_fence(fence_ref)
    assert plan == [{"tool_name": "shell_script", "args": {"script": "echo from_file"}}]

    # ref missing
    fence_missing_ref = scan_markdown_fences("```bash exec ref=missing.sh\n\n```")[0]
    assert parse_bash_exec_fence(fence_missing_ref) is None

    # ref whitespace only
    sh_blank = tmp_path / "blank.sh"
    sh_blank.write_text("   \n", encoding="utf-8")
    fence_blank_ref = scan_markdown_fences("```bash exec ref=blank.sh\n\n```")[0]
    assert parse_bash_exec_fence(fence_blank_ref) is None

    # shlex runtime parse error
    fence_bad_runtime = scan_markdown_fences(
        '```bash exec runtime="bash -c \'unclosed"\necho hi\n```'
    )[0]
    assert parse_bash_exec_fence(fence_bad_runtime) is None


def test_parse_python_exec_fence_handles_ref_and_extract(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    py_file = tmp_path / "app.py"
    py_file.write_text("print('resolved')", encoding="utf-8")

    fence_ref = scan_markdown_fences("```python exec ref=app.py\n\n```")[0]
    plan = parse_python_exec_fence(fence_ref)
    assert plan == [{"tool_name": "python_script", "args": {"script": "print('resolved')"}}]

    fence_missing = scan_markdown_fences("```python exec ref=missing.py\n\n```")[0]
    assert parse_python_exec_fence(fence_missing) is None

    plans = extract_python_exec_plans("```python exec\nprint(1)\n```")
    assert len(plans) == 1
    assert plans[0][0][0]["args"]["script"] == "print(1)"


def test_parse_powershell_exec_fence_handles_ref_and_extract(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ps_file = tmp_path / "run.ps1"
    ps_file.write_text("Write-Host 'resolved'", encoding="utf-8")

    fence_ref = scan_markdown_fences("```powershell exec ref=run.ps1\n\n```")[0]
    plan = parse_powershell_exec_fence(fence_ref)
    assert plan == [{"tool_name": "powershell_script", "args": {"script": "Write-Host 'resolved'"}}]

    fence_missing = scan_markdown_fences("```powershell exec ref=missing.ps1\n\n```")[0]
    assert parse_powershell_exec_fence(fence_missing) is None

    plans = extract_powershell_exec_plans("```powershell exec\nWrite-Host 1\n```")
    assert len(plans) == 1
    assert plans[0][0][0]["args"]["script"] == "Write-Host 1"


def test_parse_interpreter_exec_fence_handles_ref_and_extract(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    bc_file = tmp_path / "calc.bc"
    bc_file.write_text("scale=2; 1/2", encoding="utf-8")

    fence_ref = scan_markdown_fences("```bc exec runtime=bc ref=calc.bc\n\n```")[0]
    plan = parse_interpreter_exec_fence(fence_ref)
    assert plan == [
        {
            "tool_name": "interpreter_script",
            "args": {"language": "bc", "script": "scale=2; 1/2", "runtime": ["bc"]},
        }
    ]

    fence_missing = scan_markdown_fences("```bc exec runtime=bc ref=missing.bc\n\n```")[0]
    assert parse_interpreter_exec_fence(fence_missing) is None

    plans = extract_interpreter_exec_plans("```bc exec runtime=bc\n1+1\n```")
    assert len(plans) == 1
    assert plans[0][0][0]["args"]["script"] == "1+1"


def test_parse_write_fence_pure_write_and_unregistered_language():
    fence = scan_markdown_fences("```rust write path=src/main.rs\nfn main() {}\n```")[0]
    assert parse_write_fence(fence) == [
        {"tool_name": "write_file", "args": {"path": "src/main.rs", "content": "fn main() {}\n"}}
    ]

    # Inactive / unsupported fence forms
    assert parse_write_fence(scan_markdown_fences("```rust\nfn main() {}\n```")[0]) is None
    assert parse_write_fence(scan_markdown_fences("```rust exec\nfn main() {}\n```")[0]) is None


def test_parse_write_fence_with_flags_and_ref(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    data_file = tmp_path / "seed.txt"
    data_file.write_text("hello data", encoding="utf-8")

    # flags: overwrite / force and append / mode
    fence_flags = scan_markdown_fences(
        "```text write path=out.txt overwrite=true append=true\nsome content\n```"
    )[0]
    assert parse_write_fence(fence_flags) == [
        {
            "tool_name": "write_file",
            "args": {"path": "out.txt", "content": "some content\n", "force": True, "append": True},
        }
    ]

    fence_alt_flags = scan_markdown_fences(
        "```text write path=out.txt force=false mode=append\nsome content\n```"
    )[0]
    assert parse_write_fence(fence_alt_flags) == [
        {
            "tool_name": "write_file",
            "args": {
                "path": "out.txt",
                "content": "some content\n",
                "force": False,
                "append": True,
            },
        }
    ]

    # ref resolution on empty content
    fence_ref = scan_markdown_fences("```text write path=target.txt ref=seed.txt\n\n```")[0]
    assert parse_write_fence(fence_ref) == [
        {"tool_name": "write_file", "args": {"path": "target.txt", "content": "hello data"}}
    ]

    # missing ref returns None
    fence_bad_ref = scan_markdown_fences("```text write path=target.txt ref=missing.txt\n\n```")[0]
    assert parse_write_fence(fence_bad_ref) is None


def test_parse_write_fence_composite_write_and_exec():
    # python composite
    py_fence = scan_markdown_fences(
        '```python write path=app.py exec cwd=src runtime="python3" timeout_s=15 force=true\nprint("hi")\n```'
    )[0]
    assert parse_write_fence(py_fence) == [
        {
            "tool_name": "write_file",
            "args": {"path": "app.py", "content": 'print("hi")\n', "force": True},
        },
        {
            "tool_name": "python_script",
            "args": {
                "script": 'print("hi")',
                "path": "app.py",
                "persist": True,
                "cwd": "src",
                "runtime": ["python3"],
                "timeout_s": 15,
                "overwrite": True,
            },
        },
    ]

    # bash composite
    sh_fence = scan_markdown_fences(
        '```bash write path=run.sh exec runtime="sh -e" timeout_s=10\necho 123\n```'
    )[0]
    assert parse_write_fence(sh_fence) == [
        {"tool_name": "write_file", "args": {"path": "run.sh", "content": "echo 123\n"}},
        {
            "tool_name": "shell_script",
            "args": {"script": "echo 123", "runtime": ["sh", "-e"], "timeout_s": 10},
        },
    ]

    # bash composite bad runtime
    sh_bad_runtime = scan_markdown_fences(
        '```bash write path=run.sh exec runtime="sh -e \'"\necho 123\n```'
    )[0]
    assert parse_write_fence(sh_bad_runtime) is None

    # powershell composite
    ps_fence = scan_markdown_fences(
        '```powershell write path=run.ps1 exec cwd=dir runtime="pwsh" timeout_s=5\nWrite-Host 1\n```'
    )[0]
    assert parse_write_fence(ps_fence) == [
        {"tool_name": "write_file", "args": {"path": "run.ps1", "content": "Write-Host 1\n"}},
        {
            "tool_name": "powershell_script",
            "args": {
                "script": "Write-Host 1",
                "path": "run.ps1",
                "persist": True,
                "cwd": "dir",
                "runtime": ["pwsh"],
                "timeout_s": 5,
            },
        },
    ]

    # interpreter composite
    bc_fence = scan_markdown_fences("```bc write path=calc.bc exec runtime=bc\n1+1\n```")[0]
    assert parse_write_fence(bc_fence) == [
        {"tool_name": "write_file", "args": {"path": "calc.bc", "content": "1+1\n"}},
        {
            "tool_name": "interpreter_script",
            "args": {
                "language": "bc",
                "script": "1+1",
                "runtime": ["bc"],
                "path": "calc.bc",
                "persist": True,
            },
        },
    ]


def test_extract_write_fence_plans():
    content = (
        "intro\n"
        "```python write path=a.py\nx = 1\n```\n"
        "middle\n"
        "```bash write path=b.sh exec\necho b\n```\n"
    )
    plans = extract_write_fence_plans(content)
    assert len(plans) == 2
    assert plans[0][0][0]["args"]["path"] == "a.py"
    assert plans[0][1] == content.index("```python write")
    assert plans[1][0][0]["args"]["path"] == "b.sh"
    assert plans[1][0][1]["tool_name"] == "shell_script"
    assert plans[1][1] == content.index("```bash write")


def test_resolve_fence_stdin(tmp_path, monkeypatch):
    from toas.runtime.executable_fence_lanes import _resolve_fence_stdin

    monkeypatch.chdir(tmp_path)

    # Empty string returns None
    assert _resolve_fence_stdin("") is None
    assert _resolve_fence_stdin("   ") is None

    # Scratch block ID from disk
    scratch_dir = tmp_path / ".toas" / "scratch"
    scratch_dir.mkdir(parents=True)
    (scratch_dir / "ib_abc123.txt").write_text("scratch payload", encoding="utf-8")
    assert _resolve_fence_stdin("ib_abc123", workspace_root=tmp_path) == "scratch payload"
    assert _resolve_fence_stdin(".toas/scratch/ib_abc123.txt", workspace_root=tmp_path) == "scratch payload"

    # Scratch block ID from transcript content
    transcript = '```json block_id="ib_from_transcript"\n{"status": "ok"}\n```'
    assert _resolve_fence_stdin("ib_from_transcript", content=transcript, workspace_root=tmp_path) == '{"status": "ok"}'

    # Workspace file path
    data_file = tmp_path / "data.csv"
    data_file.write_text("a,b,c\n1,2,3", encoding="utf-8")
    assert _resolve_fence_stdin("data.csv", workspace_root=tmp_path) == "a,b,c\n1,2,3"

    # Fallback to .toas/scratch/<ref>.txt
    (scratch_dir / "myref.txt").write_text("fallback ref", encoding="utf-8")
    assert _resolve_fence_stdin("myref", workspace_root=tmp_path) == "fallback ref"

    # Missing file returns None
    assert _resolve_fence_stdin("nonexistent.txt", workspace_root=tmp_path) is None
    assert _resolve_fence_stdin("ib_missing", workspace_root=tmp_path) is None


def test_resolve_fence_stdin_oserror(tmp_path, monkeypatch):
    from toas.runtime.executable_fence_lanes import _resolve_fence_stdin

    monkeypatch.chdir(tmp_path)
    scratch_dir = tmp_path / ".toas" / "scratch"
    scratch_dir.mkdir(parents=True, exist_ok=True)

    # 1. Scratch block ID with OSError
    f1 = scratch_dir / "ib_err.txt"
    f1.write_text("ok")
    # 2. Workspace file with OSError
    f2 = tmp_path / "target_err.txt"
    f2.write_text("ok")
    # 3. Fallback scratch file with OSError
    f3 = scratch_dir / "ref_err.txt"
    f3.write_text("ok")

    def _mock_read_text(self, *args, **kwargs):
        raise OSError("mock read error")

    monkeypatch.setattr(Path, "read_text", _mock_read_text)

    assert _resolve_fence_stdin("ib_err", workspace_root=tmp_path) is None
    assert _resolve_fence_stdin("target_err.txt", workspace_root=tmp_path) is None
    assert _resolve_fence_stdin("ref_err", workspace_root=tmp_path) is None


def test_parse_bash_exec_fence_io_channels(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "input.txt").write_text("hello stdin", encoding="utf-8")

    fence = scan_markdown_fences(
        "```bash exec stdin=input.txt out=artifacts/build.log err=artifacts/build.err append_out=true append_err=false\n"
        "cat\n"
        "```"
    )[0]
    plan = parse_bash_exec_fence(fence)
    assert plan is not None
    assert len(plan) == 1
    call = plan[0]
    assert call["tool_name"] == "shell_script"
    assert call["args"]["script"] == "cat"
    assert call["args"]["input"] == "hello stdin"
    assert call["stdin"] == "input.txt"
    assert call["out"] == "artifacts/build.log"
    assert call["err"] == "artifacts/build.err"
    assert call["append_out"] is True
    assert "append_err" not in call  # false not stored as flag

    # Fail-closed when stdin cannot be resolved
    bad_fence = scan_markdown_fences("```bash exec stdin=missing.txt\ncat\n```")[0]
    assert parse_bash_exec_fence(bad_fence) is None


def test_parse_python_exec_fence_io_channels(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data.json").write_text('{"records": 5}', encoding="utf-8")

    fence = scan_markdown_fences(
        "```python exec stdin=data.json out=scratch err=scratch append_err=true\n"
        "import sys\nprint(sys.stdin.read())\n"
        "```"
    )[0]
    plan = parse_python_exec_fence(fence)
    assert plan is not None
    call = plan[0]
    assert call["tool_name"] == "python_script"
    assert call["args"]["input"] == '{"records": 5}'
    assert call["stdin"] == "data.json"
    assert call["out"] == "scratch"
    assert call["err"] == "scratch"
    assert call["append_err"] is True

    # Fail closed
    missing_fence = scan_markdown_fences("```python exec stdin=missing.json\nprint(1)\n```")[0]
    assert parse_python_exec_fence(missing_fence) is None


def test_parse_powershell_exec_fence_io_channels(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "input.txt").write_text("pwsh input", encoding="utf-8")

    fence = scan_markdown_fences("```powershell exec stdin=input.txt out=out.txt\nGet-Content\n```")[0]
    plan = parse_powershell_exec_fence(fence)
    assert plan is not None
    call = plan[0]
    assert call["tool_name"] == "powershell_script"
    assert call["args"]["input"] == "pwsh input"
    assert call["out"] == "out.txt"

    # Fail closed
    assert parse_powershell_exec_fence(scan_markdown_fences("```powershell exec stdin=missing.txt\nGet-Content\n```")[0]) is None


def test_parse_interpreter_exec_fence_io_channels(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "calc.in").write_text("5 + 5\n", encoding="utf-8")

    # ref or script is needed for interpreter script; provide ref
    (tmp_path / "calc.bc").write_text("read()", encoding="utf-8")
    fence_with_body = scan_markdown_fences("```bc exec runtime=bc stdin=calc.in out=calc.out\nread()\n```")[0]
    plan = parse_interpreter_exec_fence(fence_with_body)
    assert plan is not None
    call = plan[0]
    assert call["tool_name"] == "interpreter_script"
    assert call["args"]["input"] == "5 + 5\n"
    assert call["out"] == "calc.out"

    # Fail closed
    assert parse_interpreter_exec_fence(scan_markdown_fences("```bc exec runtime=bc stdin=missing.in\nread()\n```")[0]) is None


def test_parse_write_fence_io_channels(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data.csv").write_text("name,val\nfoo,42", encoding="utf-8")

    content = (
        "```python write path=transform.py exec stdin=data.csv out=data.json append_out=true\n"
        "import sys\n"
        "print(sys.stdin.read())\n"
        "```"
    )
    fence = scan_markdown_fences(content)[0]
    plan = parse_write_fence(fence, content=content)
    assert plan is not None
    assert len(plan) == 2
    assert plan[0]["tool_name"] == "write_file"
    assert plan[0]["args"]["path"] == "transform.py"

    exec_call = plan[1]
    assert exec_call["tool_name"] == "python_script"
    assert exec_call["args"]["input"] == "name,val\nfoo,42"
    assert exec_call["stdin"] == "data.csv"
    assert exec_call["out"] == "data.json"
    assert exec_call["append_out"] is True

    # Fail closed on missing stdin
    bad_content = "```python write path=transform.py exec stdin=missing.csv\nprint(1)\n```"
    assert parse_write_fence(scan_markdown_fences(bad_content)[0], content=bad_content) is None


def test_extract_plans_with_transcript_inert_block_stdin():
    transcript = (
        "Here is the data:\n"
        '```json block_id="ib_records123"\n'
        '{"count": 10}\n'
        "```\n"
        "\n"
        "Now process it:\n"
        "```python exec stdin=ib_records123 out=scratch\n"
        "import sys, json\n"
        "data = json.load(sys.stdin)\n"
        'print(f"Count is {data[\'count\']}")\n'
        "```\n"
    )
    plans = extract_python_exec_plans(transcript)
    assert len(plans) == 1
    call = plans[0][0][0]
    assert call["args"]["input"] == '{"count": 10}'
    assert call["stdin"] == "ib_records123"
    assert call["out"] == "scratch"

