from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

import pexpect


def _vim_quote(path: Path) -> str:
    return str(path).replace("'", "''")


def _scenario_config(scenario: str) -> tuple[str, str, str, str]:
    if scenario == "tool_result_scope_marker":
        event = (
            "{'lane': 'tool', 'phase': 'delta', 'seq': 1, "
            "'payload': {'text': \"## RESULT\\n\\n[OK] shell: exit=0\\nstdout:\\n/workspace\\n\"}}"
        )
        return (
            "rtoolscope1",
            "## TOAS:USER\n\n# local host tool result scope marker\n",
            event,
            "[OK] shell: exit=0",
        )
    if scenario == "tool_operation_wrapper":
        return (
            "rtoolwrapper1",
            "## TOAS:USER\n\n```yaml\n- tool_name: shell_script\n  arguments:\n    script: |\n      sleep 3\n```\n",
            "",
            "tool: shell_script",
        )
    if scenario == "tool_shell_prompt_wrapper":
        return (
            "rtoolprompt1",
            "## TOAS:USER\n\n$ sleep 3\n",
            "",
            "tool: shell",
        )
    if scenario == "tool_quoted_shell_prompt_wrapper":
        return (
            "rtoolquotedprompt1",
            "## TOAS:USER\n\n> $ sleep 3\n",
            "",
            "tool: shell",
        )
    if scenario == "tool_quoted_yaml_wrapper":
        return (
            "rtoolquotedyaml1",
            "## TOAS:USER\n\n> ```yaml\n> - tool_name: shell_script\n>   args:\n>     script: |\n>       sleep 3\n> ```\n",
            "",
            "tool: shell_script",
        )
    if scenario == "tool_immediate_wrapper":
        return (
            "rtoolimmediate1",
            "## TOAS:USER\n\n$ sleep 3\n",
            "",
            "tool: shell",
        )
    if scenario == "tool_stale_result_block":
        return (
            "rstaleresult1",
            "## TOAS:USER\n\n```yaml\n- tool_name: write_file\n  args:\n    path: x\n    content: hi\n```\n\n## RESULT\n\n[OK] write_file: wrote 2 bytes\n\n## TOAS:ASSISTANT\n\nThinking about what to do next.\n",
            "",
            "tool: write_file",
        )
    if scenario == "projection_lane":
        event = (
            "{'type': 'projection_delta', 'lane': 'projection', 'phase': 'delta', 'seq': 1, "
            "'payload': {'text': \"## TOAS:USER\\n\\n## RESULT\\n\\n```inert\\n[OK] procedure: repo_discovery_triage_v1: 4 steps\\n```\\n\", "
            "'projection': {'source': 'runtime_step', 'target': 'transcript', 'format': 'rendered_transcript', 'mode': 'append'}}}"
        )
        return (
            "rruntimeprojection1",
            "## TOAS:USER\n\n# local host runtime projection lane\n",
            event,
            "repo_discovery_triage_v1",
        )
    raise ValueError(f"unknown scenario: {scenario}")


def run(vim_bin: str, scenario: str, timeout_s: float) -> dict[str, object]:
    root = Path(__file__).resolve().parents[2]
    run_id, session_text, event_expr, required_text = _scenario_config(scenario)
    with tempfile.TemporaryDirectory(prefix="toas-vim-projection-cases-") as td:
        tdp = Path(td)
        session_path = tdp / "session.md"
        session_path.write_text(session_text, encoding="utf-8")
        out = tdp / "out.json"
        script = tdp / "script.vim"
        plugin_path = _vim_quote(root / "vim" / "plugin" / "toas.vim")
        session_quoted = _vim_quote(session_path)
        out_path = _vim_quote(out)
        if scenario == "tool_operation_wrapper":
            script_lines = [
                "set nocompatible",
                "set hidden",
                "set noswapfile",
                "set shortmess+=I",
                f"source {plugin_path}",
                "redir => g:toas_function_dump",
                "silent function /toas_render_run_lines",
                "silent function /toas_extract_frontier_tool_name_from_lines",
                "silent function /toas_note_run_kind",
                "silent function /toas_note_tool_event_meta",
                "redir END",
                "let g:render_fn = matchstr(g:toas_function_dump, '<SNR>\\d\\+_toas_render_run_lines')",
                "let g:extract_fn = matchstr(g:toas_function_dump, '<SNR>\\d\\+_toas_extract_frontier_tool_name_from_lines')",
                "let g:kind_fn = matchstr(g:toas_function_dump, '<SNR>\\d\\+_toas_note_run_kind')",
                "let g:tool_meta_fn = matchstr(g:toas_function_dump, '<SNR>\\d\\+_toas_note_tool_event_meta')",
                "let g:frontier_lines = [",
                "      \\ '## TOAS:USER',",
                "      \\ '',",
                "      \\ '```yaml',",
                "      \\ '- tool_name: shell_script',",
                "      \\ '  arguments:',",
                "      \\ '    script: |',",
                "      \\ '      sleep 3',",
                "      \\ '```',",
                "      \\ ]",
                "let g:tool_name = call(function(g:extract_fn), [g:frontier_lines])",
                f"call call(function(g:kind_fn), ['{run_id}', 'tool'])",
                "call call(function(g:tool_meta_fn), ['" + run_id + "', {'lane': 'tool', 'payload': {'operation': g:tool_name}}])",
                f"let g:rendered_lines = call(function(g:render_fn), ['{run_id}', 'running', \"## RESULT\\n\\n[OK] shell: exit=0\\nstdout:\\nhello\\n\", ''])",
                f"let g:run_id = '{run_id}'",
                "let g:result = {",
                "      \\ 'run_id': g:run_id,",
                "      \\ 'status': 'running',",
                "      \\ 'run_kind': get(g:, 'toas_last_run_kind', ''),",
                "      \\ 'error': get(g:, 'toas_last_error', ''),",
                "      \\ 'transport': '',",
                "      \\ 'text': join(g:rendered_lines, \"\\n\"),",
                "      \\ }",
                f"call writefile([json_encode(g:result)], '{out_path}')",
                "qa!",
            ]
        elif scenario == "tool_shell_prompt_wrapper":
            script_lines = [
                "set nocompatible",
                "set hidden",
                "set noswapfile",
                "set shortmess+=I",
                f"source {plugin_path}",
                "redir => g:toas_function_dump",
                "silent function /toas_render_run_lines",
                "silent function /toas_extract_frontier_tool_name_from_lines",
                "silent function /toas_note_run_kind",
                "silent function /toas_note_tool_event_meta",
                "redir END",
                "let g:render_fn = matchstr(g:toas_function_dump, '<SNR>\\d\\+_toas_render_run_lines')",
                "let g:extract_fn = matchstr(g:toas_function_dump, '<SNR>\\d\\+_toas_extract_frontier_tool_name_from_lines')",
                "let g:kind_fn = matchstr(g:toas_function_dump, '<SNR>\\d\\+_toas_note_run_kind')",
                "let g:tool_meta_fn = matchstr(g:toas_function_dump, '<SNR>\\d\\+_toas_note_tool_event_meta')",
                "let g:frontier_lines = ['## TOAS:USER', '', '$ sleep 3']",
                "let g:tool_name = call(function(g:extract_fn), [g:frontier_lines])",
                f"call call(function(g:kind_fn), ['{run_id}', 'tool'])",
                "call call(function(g:tool_meta_fn), ['" + run_id + "', {'lane': 'tool', 'payload': {'operation': g:tool_name}}])",
                f"let g:rendered_lines = call(function(g:render_fn), ['{run_id}', 'running', \"## RESULT\\n\\n[OK] shell: exit=0\\nstdout:\\nhello\\n\", ''])",
                f"let g:run_id = '{run_id}'",
                "let g:result = {",
                "      \\ 'run_id': g:run_id,",
                "      \\ 'status': 'running',",
                "      \\ 'run_kind': get(g:, 'toas_last_run_kind', ''),",
                "      \\ 'error': get(g:, 'toas_last_error', ''),",
                "      \\ 'transport': '',",
                "      \\ 'text': join(g:rendered_lines, \"\\n\"),",
                "      \\ }",
                f"call writefile([json_encode(g:result)], '{out_path}')",
                "qa!",
            ]
        elif scenario == "tool_quoted_shell_prompt_wrapper":
            script_lines = [
                "set nocompatible",
                "set hidden",
                "set noswapfile",
                "set shortmess+=I",
                f"source {plugin_path}",
                "redir => g:toas_function_dump",
                "silent function /toas_render_run_lines",
                "silent function /toas_extract_frontier_tool_name_from_lines",
                "silent function /toas_note_run_kind",
                "silent function /toas_note_tool_event_meta",
                "redir END",
                "let g:render_fn = matchstr(g:toas_function_dump, '<SNR>\\d\\+_toas_render_run_lines')",
                "let g:extract_fn = matchstr(g:toas_function_dump, '<SNR>\\d\\+_toas_extract_frontier_tool_name_from_lines')",
                "let g:kind_fn = matchstr(g:toas_function_dump, '<SNR>\\d\\+_toas_note_run_kind')",
                "let g:tool_meta_fn = matchstr(g:toas_function_dump, '<SNR>\\d\\+_toas_note_tool_event_meta')",
                "let g:frontier_lines = ['## TOAS:USER', '', '> $ sleep 3']",
                "let g:tool_name = call(function(g:extract_fn), [g:frontier_lines])",
                f"call call(function(g:kind_fn), ['{run_id}', 'tool'])",
                "call call(function(g:tool_meta_fn), ['" + run_id + "', {'lane': 'tool', 'payload': {'operation': g:tool_name}}])",
                f"let g:rendered_lines = call(function(g:render_fn), ['{run_id}', 'running', \"## RESULT\\n\\n[OK] shell: exit=0\\nstdout:\\nhello\\n\", ''])",
                f"let g:run_id = '{run_id}'",
                "let g:result = {",
                "      \\ 'run_id': g:run_id,",
                "      \\ 'status': 'running',",
                "      \\ 'run_kind': get(g:, 'toas_last_run_kind', ''),",
                "      \\ 'error': get(g:, 'toas_last_error', ''),",
                "      \\ 'transport': '',",
                "      \\ 'text': join(g:rendered_lines, \"\\n\"),",
                "      \\ }",
                f"call writefile([json_encode(g:result)], '{out_path}')",
                "qa!",
            ]
        elif scenario == "tool_quoted_yaml_wrapper":
            script_lines = [
                "set nocompatible",
                "set hidden",
                "set noswapfile",
                "set shortmess+=I",
                f"source {plugin_path}",
                "redir => g:toas_function_dump",
                "silent function /toas_render_run_lines",
                "silent function /toas_extract_frontier_tool_name_from_lines",
                "silent function /toas_note_run_kind",
                "silent function /toas_note_tool_event_meta",
                "redir END",
                "let g:render_fn = matchstr(g:toas_function_dump, '<SNR>\\d\\+_toas_render_run_lines')",
                "let g:extract_fn = matchstr(g:toas_function_dump, '<SNR>\\d\\+_toas_extract_frontier_tool_name_from_lines')",
                "let g:kind_fn = matchstr(g:toas_function_dump, '<SNR>\\d\\+_toas_note_run_kind')",
                "let g:tool_meta_fn = matchstr(g:toas_function_dump, '<SNR>\\d\\+_toas_note_tool_event_meta')",
                "let g:frontier_lines = [",
                "      \\ '## TOAS:USER',",
                "      \\ '',",
                "      \\ '> ```yaml',",
                "      \\ '> - tool_name: shell_script',",
                "      \\ '>   args:',",
                "      \\ '>     script: |',",
                "      \\ '>       sleep 3',",
                "      \\ '> ```',",
                "      \\ ]",
                "let g:tool_name = call(function(g:extract_fn), [g:frontier_lines])",
                f"call call(function(g:kind_fn), ['{run_id}', 'tool'])",
                "call call(function(g:tool_meta_fn), ['" + run_id + "', {'lane': 'tool', 'payload': {'operation': g:tool_name}}])",
                f"let g:rendered_lines = call(function(g:render_fn), ['{run_id}', 'running', \"## RESULT\\n\\n[OK] shell: exit=0\\nstdout:\\nhello\\n\", ''])",
                f"let g:run_id = '{run_id}'",
                "let g:result = {",
                "      \\ 'run_id': g:run_id,",
                "      \\ 'status': 'running',",
                "      \\ 'run_kind': get(g:, 'toas_last_run_kind', ''),",
                "      \\ 'error': get(g:, 'toas_last_error', ''),",
                "      \\ 'transport': '',",
                "      \\ 'text': join(g:rendered_lines, \"\\n\"),",
                "      \\ }",
                f"call writefile([json_encode(g:result)], '{out_path}')",
                "qa!",
            ]
        elif scenario == "tool_immediate_wrapper":
            script_lines = [
                "set nocompatible",
                "set hidden",
                "set noswapfile",
                "set shortmess+=I",
                f"source {plugin_path}",
                "let g:toas_step_nonblocking = 1",
                "let g:toas_notice_enabled = 0",
                "let g:toas_transport_mode = 'local_host'",
                "let g:toas_step_lane_order = ['default']",
                "function! g:ToasLocalHostProjectionCases(op, payload, timeout_s) abort",
                "  if a:op ==# 'step_async'",
                f"    return {{'ok': v:true, 'payload': {{'run_id': '{run_id}', 'status': 'running', 'stream_policy': {{}}}}}}",
                "  endif",
                "  throw 'unexpected op=' . a:op",
                "endfunction",
                "let g:ToasTestLocalHostRequestFn = function('g:ToasLocalHostProjectionCases')",
                f"execute 'edit ' . fnameescape('{session_quoted}')",
                "write",
                "call ToasStep()",
                "let g:run_id = get(g:, 'toas_active_run_id', '')",
                "let g:result = {",
                "      \\ 'run_id': g:run_id,",
                "      \\ 'status': get(g:, 'toas_last_run_status', ''),",
                "      \\ 'run_kind': get(g:, 'toas_last_run_kind', ''),",
                "      \\ 'error': get(g:, 'toas_last_error', ''),",
                "      \\ 'transport': get(g:, 'toas_last_step_transport', ''),",
                "      \\ 'text': join(getline(1, '$'), \"\\n\"),",
                "      \\ }",
                f"call writefile([json_encode(g:result)], '{out_path}')",
                "qa!",
            ]
        elif scenario == "tool_stale_result_block":
            script_lines = [
                "set nocompatible",
                "set hidden",
                "set noswapfile",
                "set shortmess+=I",
                f"source {plugin_path}",
                "redir => g:toas_function_dump",
                "silent function /toas_extract_frontier_tool_name_from_lines",
                "redir END",
                "let g:extract_fn = matchstr(g:toas_function_dump, '<SNR>\\d\\+_toas_extract_frontier_tool_name_from_lines')",
                "let g:frontier_lines = [",
                "      \\ '## TOAS:USER',",
                "      \\ '',",
                "      \\ '```yaml',",
                "      \\ '- tool_name: write_file',",
                "      \\ '  args:',",
                "      \\ '    path: x',",
                "      \\ '    content: hi',",
                "      \\ '```',",
                "      \\ '',",
                "      \\ '## RESULT',",
                "      \\ '',",
                "      \\ '[OK] write_file: wrote 2 bytes',",
                "      \\ '',",
                "      \\ '## TOAS:ASSISTANT',",
                "      \\ '',",
                "      \\ 'Thinking about what to do next.',",
                "      \\ ]",
                "let g:tool_name = call(function(g:extract_fn), [g:frontier_lines])",
                "let g:result = {'run_id': '', 'status': '', 'run_kind': '', 'error': '', 'transport': '', 'text': g:tool_name}",
                f"call writefile([json_encode(g:result)], '{out_path}')",
                "qa!",
            ]
        else:
            script_lines = [
                "set nocompatible",
                "set hidden",
                "set noswapfile",
                "set shortmess+=I",
                f"source {plugin_path}",
                "let g:toas_step_nonblocking = 1",
                "let g:toas_notice_enabled = 0",
                "let g:toas_transport_mode = 'local_host'",
                "let g:toas_step_lane_order = ['default']",
                "function! g:ToasLocalHostProjectionCases(op, payload, timeout_s) abort",
                "  if a:op ==# 'step_async'",
                f"    return {{'ok': v:true, 'payload': {{'run_id': '{run_id}', 'status': 'running', 'stream_policy': {{}}}}}}",
                "  endif",
                "  if a:op ==# 'watch'",
                "    return {'ok': v:true, 'payload': {'status': 'running', 'chunk': '', 'next_offset': 0, 'next_seq': 0, 'events': []}}",
                "  endif",
                "  throw 'unexpected op=' . a:op",
                "endfunction",
                "function! g:ToasLocalHostProjectionCaseFrames(run_id, timeout_s) abort",
                "  return [",
                "        \\ {'ok': v:true, 'request_id': 'sub-1', 'payload': {'kind': 'push_ack', 'run_id': a:run_id}},",
                f"        \\ {{'ok': v:true, 'request_id': 'sub-1', 'payload': {{'kind': 'push_event', 'run_id': a:run_id, 'event': {event_expr}}}}},",
                "        \\ {'ok': v:true, 'request_id': 'sub-1', 'payload': {'kind': 'push_event', 'run_id': a:run_id, 'event': {'type': 'run_done', 'lane': 'run', 'phase': 'end', 'seq': 2, 'payload': {'status': 'succeeded'}}}},",
                "        \\ {'ok': v:true, 'request_id': 'sub-1', 'payload': {'kind': 'push_complete', 'run_id': a:run_id, 'complete': v:true}},",
                "        \\ ]",
                "endfunction",
                "let g:ToasTestLocalHostRequestFn = function('g:ToasLocalHostProjectionCases')",
                "let g:ToasTestLocalHostSubscribeFn = function('g:ToasLocalHostProjectionCaseFrames')",
                f"execute 'edit ' . fnameescape('{session_quoted}')",
                "write",
                "call ToasStepAsync()",
                "let g:run_id = get(g:, 'toas_active_run_id', '')",
                "if g:run_id !=# ''",
                "  call ToasWatch(g:run_id, '--follow')",
                "endif",
                "let g:result = {",
                "      \\ 'run_id': g:run_id,",
                "      \\ 'status': get(g:, 'toas_last_run_status', ''),",
                "      \\ 'run_kind': get(g:, 'toas_last_run_kind', ''),",
                "      \\ 'error': get(g:, 'toas_last_error', ''),",
                "      \\ 'transport': get(g:, 'toas_last_step_transport', ''),",
                "      \\ 'text': join(getline(1, '$'), \"\\n\"),",
                "      \\ }",
                f"call writefile([json_encode(g:result)], '{out_path}')",
                "qa!",
            ]
        script.write_text("\n".join(script_lines) + "\n", encoding="utf-8")

        child = pexpect.spawn(
            vim_bin,
            ["-Nu", "NONE", "-n", "-i", "NONE", "-S", str(script)],
            cwd=str(tdp),
            encoding="utf-8",
            timeout=timeout_s,
        )
        child.expect(pexpect.EOF)
        child.close()
        if not out.exists():
            return {
                "ok": False,
                "result": None,
                "stdout_tail": child.before[-1200:] if isinstance(child.before, str) else "",
            }
        result = json.loads(out.read_text(encoding="utf-8").strip())
        ok = (
            result.get("run_id", "") == run_id
            and result.get("status") == "succeeded"
            and "## TOAS:USER" in result.get("text", "")
            and "## RESULT" in result.get("text", "")
            and required_text in result.get("text", "")
        )
        if scenario in {"tool_operation_wrapper", "tool_shell_prompt_wrapper", "tool_quoted_shell_prompt_wrapper", "tool_quoted_yaml_wrapper"}:
            ok = (
                result.get("run_id", "") == run_id
                and result.get("status") == "running"
                and "## TOAS:RUN " in result.get("text", "")
                and required_text in result.get("text", "")
            )
        if scenario == "tool_immediate_wrapper":
            ok = (
                result.get("run_id", "") == run_id
                and result.get("status") == "running"
                and result.get("transport", "").startswith("local_host_")
                and "## TOAS:RUN " in result.get("text", "")
                and required_text in result.get("text", "")
            )
        if scenario == "tool_stale_result_block":
            ok = result.get("text", '') == ''
        if scenario == "projection_lane":
            ok = ok and "## TOAS:ASSISTANT" not in result.get("text", "")
        return {"ok": ok, "result": result}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vim-bin", default="vim")
    ap.add_argument("--scenario", required=True)
    ap.add_argument("--timeout-s", type=float, default=12.0)
    ns = ap.parse_args()
    out = run(ns.vim_bin, ns.scenario, ns.timeout_s)
    print(json.dumps(out, sort_keys=True))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
