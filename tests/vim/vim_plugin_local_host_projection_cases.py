from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from vim_terminal import EOF, spawn


def _vim_quote(path: Path) -> str:
    return path.as_posix().replace("'", "''")


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
            "",
        )
    if scenario == "tool_quoted_yaml_wrapper":
        return (
            "rtoolquotedyaml1",
            "## TOAS:USER\n\n> ```yaml\n> - tool_name: shell_script\n>   args:\n>     script: |\n>       sleep 3\n> ```\n",
            "",
            "",
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
    if scenario == "state_projection_lane":
        event = (
            "{'type': 'projection_delta', 'lane': 'projection', 'phase': 'delta', 'seq': 1, "
            "'payload': {'text': \"\\n\\n## TOAS:STATE/2\\n\\nstate:\\n  goal: step2\\n\", "
            "'projection': {'source': 'runtime_step', 'target': 'transcript', 'format': 'rendered_transcript', 'mode': 'append'}}}"
        )
        return (
            "rstateprojection1",
            "## TOAS:USER\n\nstart\n\n## TOAS:STATE/1\n\ninstructions: test\nstate:\n  goal: step1\n",
            event,
            "## TOAS:STATE/2",
        )
    if scenario == "tool_python_code_block_wrapper":
        return (
            "rtoolpyblock1",
            "## TOAS:USER\n\n```python\ndef execute(\n    operation: str,\n):\n    pass\n```",
            "",
            "",
        )
    if scenario == "tool_prose_annotation_wrapper":
        return (
            "rtoolprose1",
            "## TOAS:USER\n\noperation: str,",
            "",
            "",
        )
    if scenario == "speculative_tool_overridden_by_llm":
        event = (
            "{'lane': 'llm_answer', 'phase': 'delta', 'seq': 1, "
            "'payload': {'text': 'Hello world stream'}}"
        )
        return (
            "rspecllm1",
            "## TOAS:USER\n\n```yaml\n- tool_name: shell\n```\n",
            event,
            "Hello world stream",
        )
    if scenario == "tool_batch_progress_multi_wrapper":
        return ("rbatchmulti1", "## TOAS:USER\n", "", "")
    if scenario == "tool_batch_progress_single_wrapper":
        return ("rbatchsingle1", "## TOAS:USER\n", "", "")
    if scenario == "tool_silent_watch_events_wrapper":
        return ("rsilentwatch1", "## TOAS:USER\n", "", "")
    if scenario == "state_invalid_response_preview_replacement_wrapper":
        return ("rstateinv1", "## TOAS:USER\n", "", "")
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
                "silent function /toas_extract_frontier_tool_name_from_lines",
                "redir END",
                "let g:extract_fn = matchstr(g:toas_function_dump, '<SNR>\\d\\+_toas_extract_frontier_tool_name_from_lines')",
                "let g:frontier_lines = ['## TOAS:USER', '', '> $ sleep 3']",
                "let g:tool_name = call(function(g:extract_fn), [g:frontier_lines])",
                "let g:result = {",
                "      \\ 'run_id': '',",
                "      \\ 'status': '',",
                "      \\ 'run_kind': '',",
                "      \\ 'error': '',",
                "      \\ 'transport': '',",
                "      \\ 'text': g:tool_name,",
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
                "silent function /toas_extract_frontier_tool_name_from_lines",
                "redir END",
                "let g:extract_fn = matchstr(g:toas_function_dump, '<SNR>\\d\\+_toas_extract_frontier_tool_name_from_lines')",
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
                "let g:result = {",
                "      \\ 'run_id': '',",
                "      \\ 'status': '',",
                "      \\ 'run_kind': '',",
                "      \\ 'error': '',",
                "      \\ 'transport': '',",
                "      \\ 'text': g:tool_name,",
                "      \\ }",
                f"call writefile([json_encode(g:result)], '{out_path}')",
                "qa!",
            ]
        elif scenario in {"tool_python_code_block_wrapper", "tool_prose_annotation_wrapper"}:
            escaped_frontier = [f"      \\ '{line}'," for line in session_text.rstrip().split("\n")]
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
                *escaped_frontier,
                "      \\ ]",
                "let g:tool_name = call(function(g:extract_fn), [g:frontier_lines])",
                "let g:result = {",
                "      \\ 'run_id': '',",
                "      \\ 'status': '',",
                "      \\ 'run_kind': '',",
                "      \\ 'error': '',",
                "      \\ 'transport': '',",
                "      \\ 'text': g:tool_name,",
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
        elif scenario == "tool_batch_progress_multi_wrapper":
            script_lines = [
                "set nocompatible",
                "set hidden",
                "set noswapfile",
                "set shortmess+=I",
                f"source {plugin_path}",
                "redir => g:toas_function_dump",
                "silent function /toas_render_run_lines",
                "silent function /toas_note_run_kind",
                "silent function /toas_note_tool_event_meta",
                "redir END",
                "let g:render_fn = matchstr(g:toas_function_dump, '<SNR>\\d\\+_toas_render_run_lines')",
                "let g:kind_fn = matchstr(g:toas_function_dump, '<SNR>\\d\\+_toas_note_run_kind')",
                "let g:tool_meta_fn = matchstr(g:toas_function_dump, '<SNR>\\d\\+_toas_note_tool_event_meta')",
                f"call call(function(g:kind_fn), ['{run_id}', 'tool'])",
                f"call call(function(g:tool_meta_fn), ['{run_id}', {{'lane': 'tool', 'payload': {{'operation': 'read_file', 'index': 1, 'total': 2}}}}])",
                f"let g:render1 = call(function(g:render_fn), ['{run_id}', 'running', '', ''])",
                f"call call(function(g:tool_meta_fn), ['{run_id}', {{'lane': 'tool', 'payload': {{'operation': 'write_file', 'index': 2, 'total': 2}}}}])",
                f"let g:render2 = call(function(g:render_fn), ['{run_id}', 'running', '', ''])",
                "let g:result = {",
                f"      \\ 'run_id': '{run_id}',",
                "      \\ 'status': 'running',",
                "      \\ 'run_kind': 'tool',",
                "      \\ 'step1': join(g:render1, \"\\n\"),",
                "      \\ 'step2': join(g:render2, \"\\n\"),",
                "      \\ 'text': join(g:render2, \"\\n\"),",
                "      \\ }",
                f"call writefile([json_encode(g:result)], '{out_path}')",
                "qa!",
            ]
        elif scenario == "tool_batch_progress_single_wrapper":
            script_lines = [
                "set nocompatible",
                "set hidden",
                "set noswapfile",
                "set shortmess+=I",
                f"source {plugin_path}",
                "redir => g:toas_function_dump",
                "silent function /toas_render_run_lines",
                "silent function /toas_note_run_kind",
                "silent function /toas_note_tool_event_meta",
                "redir END",
                "let g:render_fn = matchstr(g:toas_function_dump, '<SNR>\\d\\+_toas_render_run_lines')",
                "let g:kind_fn = matchstr(g:toas_function_dump, '<SNR>\\d\\+_toas_note_run_kind')",
                "let g:tool_meta_fn = matchstr(g:toas_function_dump, '<SNR>\\d\\+_toas_note_tool_event_meta')",
                f"call call(function(g:kind_fn), ['{run_id}', 'tool'])",
                f"call call(function(g:tool_meta_fn), ['{run_id}', {{'lane': 'tool', 'payload': {{'operation': 'read_file', 'index': 1, 'total': 1}}}}])",
                f"let g:rendered = call(function(g:render_fn), ['{run_id}', 'running', '', ''])",
                "let g:result = {",
                f"      \\ 'run_id': '{run_id}',",
                "      \\ 'status': 'running',",
                "      \\ 'run_kind': 'tool',",
                "      \\ 'text': join(g:rendered, \"\\n\"),",
                "      \\ }",
                f"call writefile([json_encode(g:result)], '{out_path}')",
                "qa!",
            ]
        elif scenario == "tool_silent_watch_events_wrapper":
            script_lines = [
                "set nocompatible",
                "set hidden",
                "set noswapfile",
                "set shortmess+=I",
                f"source {plugin_path}",
                "redir => g:toas_function_dump",
                "silent function /toas_apply_watch_events",
                "redir END",
                "let g:apply_fn = matchstr(g:toas_function_dump, '<SNR>\\d\\+_toas_apply_watch_events')",
                "let g:events = [{'type': 'tool_start', 'lane': 'tool', 'phase': 'start', 'payload': {'operation': 'search', 'index': 1, 'total': 3}}, {'type': 'tool_done', 'lane': 'tool', 'phase': 'end', 'payload': {'operation': 'search', 'ok': v:true}}, {'type': 'tool_start', 'lane': 'tool', 'phase': 'start', 'payload': {'operation': 'read_file', 'index': 2, 'total': 3}}]",
                f"let g:apply_result = call(function(g:apply_fn), ['{run_id}', g:events])",
                "let g:result = {",
                f"      \\ 'run_id': '{run_id}',",
                "      \\ 'status': 'running',",
                "      \\ 'tool_changed': get(g:apply_result, 'tool_changed', 0),",
                "      \\ 'text': string(g:apply_result),",
                "      \\ }",
                f"call writefile([json_encode(g:result)], '{out_path}')",
                "qa!",
            ]
        elif scenario == "state_invalid_response_preview_replacement_wrapper":
            script_lines = [
                "set nocompatible",
                "set hidden",
                "set noswapfile",
                "set shortmess+=I",
                f"source {plugin_path}",
                "redir => g:toas_function_dump",
                "silent function /toas_apply_watch_events",
                "silent function /toas_insert_run_region",
                "silent function /toas_finalize_terminal_run_region",
                "redir END",
                "let g:apply_fn = matchstr(g:toas_function_dump, '<SNR>\\d\\+_toas_apply_watch_events')",
                "let g:insert_fn = matchstr(g:toas_function_dump, '<SNR>\\d\\+_toas_insert_run_region')",
                "let g:finalize_fn = matchstr(g:toas_function_dump, '<SNR>\\d\\+_toas_finalize_terminal_run_region')",
                "new",
                "call append(0, ['## TOAS:STATE/1', 'state:', '  goal: test'])",
                f"call call(function(g:insert_fn), ['{run_id}', 'running', line('$')])",
                "let g:events = [{'type': 'llm_delta', 'lane': 'llm_answer', 'phase': 'delta', 'seq': 1, 'payload': {'text': '{\"state_patch\": broken'}}, {'type': 'projection_delta', 'lane': 'projection', 'phase': 'delta', 'seq': 2, 'payload': {'text': \"\\n\\n## TOAS:USER\\n\\n## RESULT\\n\\n[ERROR] invalid state-step JSON response\\n\"}}, {'type': 'error', 'lane': 'llm_answer', 'phase': 'end', 'seq': 3, 'payload': {'status': 'failed', 'message': 'invalid state-step JSON response'}}]",
                f"call call(function(g:apply_fn), ['{run_id}', g:events])",
                f"call call(function(g:finalize_fn), ['{run_id}', 'failed', 'invalid state-step JSON response'])",
                "let g:lines = getline(1, '$')",
                "let g:result = {",
                f"      \\ 'run_id': '{run_id}',",
                "      \\ 'lines': g:lines,",
                "      \\ 'text': join(g:lines, \"\\n\"),",
                "      \\ }",
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

        child = spawn(
            vim_bin,
            ["-Nu", "NONE", "-n", "-i", "NONE", "-S", script.as_posix()],
            cwd=str(tdp),
            encoding="utf-8",
            timeout=timeout_s,
        )
        child.expect(EOF)
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
            if scenario in {"tool_quoted_shell_prompt_wrapper", "tool_quoted_yaml_wrapper"}:
                ok = result.get("text", '') == ''
            else:
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
        if scenario == "state_projection_lane":
            ok = (
                result.get("run_id", "") == run_id
                and result.get("status") == "succeeded"
                and "## TOAS:STATE/1" in result.get("text", "")
                and required_text in result.get("text", "")
                and "## TOAS:ASSISTANT" not in result.get("text", "")
            )
        if scenario in {"tool_python_code_block_wrapper", "tool_prose_annotation_wrapper"}:
            ok = result.get("text", "") == ""
        if scenario == "speculative_tool_overridden_by_llm":
            ok = (
                result.get("run_id", "") == run_id
                and result.get("run_kind") == "llm"
                and "tool: shell" not in result.get("text", "")
                and required_text in result.get("text", "")
            )
        if scenario == "tool_batch_progress_multi_wrapper":
            ok = (
                result.get("run_id", "") == run_id
                and "tool: read_file (1/2)" in str(result.get("step1", ""))
                and "tool: write_file (2/2)" in str(result.get("step2", ""))
            )
        if scenario == "tool_batch_progress_single_wrapper":
            ok = (
                result.get("run_id", "") == run_id
                and "tool: read_file" in str(result.get("text", ""))
                and "(1/1)" not in str(result.get("text", ""))
            )
        if scenario == "tool_silent_watch_events_wrapper":
            ok = (
                result.get("run_id", "") == run_id
                and result.get("tool_changed") == 1
            )
        if scenario == "state_invalid_response_preview_replacement_wrapper":
            ok = (
                result.get("run_id", "") == run_id
                and "[ERROR] invalid state-step JSON response" in result.get("text", "")
                and '{"state_patch": broken' not in result.get("text", "")
            )
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
