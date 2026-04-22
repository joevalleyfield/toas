from __future__ import annotations

import importlib
from pathlib import Path

from ..config import OperatorConfig


def execute_operator_command(
    command: str,
    args: list[str],
    *,
    execute,
    working: list[dict],
    transcript: str,
    command_cwd: str,
    previous_command_cwd: str | None,
    workspace_mode: str,
    workspace_roots: list[str],
    config: OperatorConfig,
    config_sources: dict[str, str] | None = None,
    already_executed_indices: set[int] | None = None,
) -> list[dict]:
    # Transitional boundary: delegate helper references through the legacy step module
    # while moving operator-command dispatch ownership into runtime.
    step_mod = importlib.import_module("toas.step")

    if command == "prompts":
        if len(args) > 1:
            raise ValueError("usage: /prompts [prefix]")
        content = step_mod._render_prompt_browse_commands(args[0] if args else None)
        return [{"role": "result", "content": content}]

    if command == "prompt":
        if len(args) > 1:
            raise ValueError("usage: /prompt [ref_or_prefix]")
        if not args:
            return [{"role": "result", "content": step_mod._render_prompt_browse_commands(None)}]
        ref_or_prefix = args[0]
        exact = None
        try:
            exact = step_mod.load_prompt_ref(
                ref_or_prefix,
                policy=step_mod.generation_policy_from_config(config),
                capability_profile=config.capability_advertisement.profile,
                capability_hidden_tools=config.capability_advertisement.hidden_tools,
            )
        except RuntimeError:
            exact = None
        if exact is not None:
            return [{"role": "result", "content": exact}]
        content = step_mod._render_prompt_browse_commands(ref_or_prefix)
        if not content:
            raise ValueError(f"unknown prompt ref or prefix: {ref_or_prefix}")
        return [{"role": "result", "content": content}]

    if command == "backend":
        if len(args) > 1:
            raise ValueError("usage: /backend [id]")
        available = step_mod._available_backends(config)
        if not args:
            if not available:
                return [{"role": "result", "content": "no backends available in current capability space"}]
            lines = ["available backends:"]
            lines.extend(f"/backend {name}" for name in available)
            return [{"role": "result", "content": "\n".join(lines)}]
        selected = args[0]
        lines = [f"selected backend intent: {selected}", "validation: deferred until inference frontier"]
        if available and selected not in available:
            lines.extend(["", "chosen backend unavailable in current capability space", "choose one of:"])
            lines.extend(f"/backend {name}" for name in available)
        return [{"role": "result", "content": "\n".join(lines)}]

    if command == "model":
        if len(args) > 1:
            raise ValueError("usage: /model [name]")
        selected_backend = step_mod.resolve_selected_backend(working)
        available = step_mod._available_models(config, selected_backend=selected_backend)
        if not args:
            if not available:
                return [{"role": "result", "content": "no models available in current capability space"}]
            lines = ["available models:"]
            lines.extend(f"/model {name}" for name in available)
            return [{"role": "result", "content": "\n".join(lines)}]
        selected = args[0]
        lines = [f"selected model intent: {selected}", "validation: deferred until inference frontier"]
        if available and selected not in available:
            lines.extend(["", "chosen model unavailable in current capability space", "choose one of:"])
            lines.extend(f"/model {name}" for name in available)
        return [{"role": "result", "content": "\n".join(lines)}]

    if command == "env":
        if not args:
            return [{"role": "result", "content": "/env set <KEY> <VALUE>\n/env unset <KEY>"}]
        if len(args) == 3 and args[0] == "set":
            key, value = args[1], args[2]
            if not step_mod.re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
                raise ValueError("invalid env key")
            return [{"role": "result", "content": f"env set: {key}"}]
        if len(args) == 2 and args[0] == "unset":
            key = args[1]
            if not step_mod.re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
                raise ValueError("invalid env key")
            return [{"role": "result", "content": f"env unset: {key}"}]
        raise ValueError("usage: /env [set <KEY> <VALUE> | unset <KEY>]")

    if command == "shell":
        if args and args[0] == "config":
            if len(args) < 2 or args[1] == "list":
                baseline = tuple(sorted(step_mod.normalize_shell_grants(config.shell.allowed_commands if config.shell.allowed_commands else step_mod.SHELL_ALLOWED)))
                return [{"role": "result", "content": "config shell grants:\n" + (", ".join(baseline) if baseline else "(none)")}]
            sub = args[1]
            if sub in {"add", "remove"}:
                if len(args) != 3:
                    raise ValueError(f"usage: {step_mod.SHELL_CONFIG_USAGE}")
                try:
                    grant = step_mod.parse_shell_grant(args[2]).raw
                except ValueError as exc:
                    raise ValueError(str(exc)) from exc
                baseline = set(step_mod.normalize_shell_grants(config.shell.allowed_commands if config.shell.allowed_commands else step_mod.SHELL_ALLOWED))
                if sub == "add":
                    baseline.add(grant)
                else:
                    baseline.discard(grant)
                updated = tuple(sorted(baseline))
                return [
                    {
                        "role": "result",
                        "content": f"config shell grants updated: {sub} {grant}\nconfig baseline: {', '.join(updated) if updated else '(none)'}",
                        "config_update": {"shell": {"allowed_commands": updated}},
                    }
                ]
            if sub == "reset":
                if len(args) != 2:
                    raise ValueError(f"usage: {step_mod.SHELL_CONFIG_USAGE}")
                defaults = tuple(sorted(step_mod.normalize_shell_grants(step_mod.SHELL_ALLOWED)))
                return [
                    {
                        "role": "result",
                        "content": f"config shell grants reset to defaults\nconfig baseline: {', '.join(defaults)}",
                        "config_update": {"shell": {"allowed_commands": defaults}},
                    }
                ]
            raise ValueError(f"usage: {step_mod.SHELL_CONFIG_USAGE}")

        if not args or args[0] == "list":
            effective, baseline, sources, transcript_added, transcript_removed = step_mod._resolve_shell_grants_with_sources(working, config)
            return [
                {
                    "role": "result",
                    "content": step_mod.render_shell_policy_view(
                        effective,
                        baseline,
                        sources,
                        transcript_added,
                        transcript_removed,
                    ),
                }
            ]
        if len(args) == 2 and args[0] in {"allow", "deny", "add", "remove", "unset"}:
            try:
                grant = step_mod.parse_shell_grant(args[1]).raw
            except ValueError as exc:
                raise ValueError(str(exc)) from exc
            effective = step_mod.resolve_effective_shell_allowed(working, config)
            return [{"role": "result", "content": f"shell grant updated: {args[0]} {grant}\neffective: {', '.join(effective)}"}]
        if len(args) == 1 and args[0] == "reset":
            effective = step_mod.resolve_effective_shell_allowed(working, config)
            return [{"role": "result", "content": f"shell grants reset to config baseline\neffective: {', '.join(effective)}"}]
        raise ValueError(f"usage: {step_mod.SHELL_USAGE}")

    if command == "pwd":
        if args:
            raise ValueError("usage: /pwd")
        return [{"role": "result", "content": str(Path(command_cwd).expanduser().resolve())}]

    if command == "cd":
        if len(args) != 1:
            raise ValueError("usage: /cd <path>|-")

        raw_target = args[0]
        if raw_target == "-":
            if previous_command_cwd is None:
                raise ValueError("no previous command cwd")
            target = Path(previous_command_cwd).expanduser().resolve()
        else:
            base = Path(command_cwd).expanduser().resolve()
            candidate = Path(raw_target).expanduser()
            target = candidate.resolve() if candidate.is_absolute() else (base / candidate).resolve()

        if not target.is_dir():
            raise ValueError(f"not a directory: {raw_target}")
        if workspace_mode == "strict":
            allowed = any(target == Path(root) or Path(root) in target.parents for root in workspace_roots)
            if not allowed:
                raise ValueError("cwd outside allowed workspace roots")

        return [
            {
                "role": "result",
                "content": str(target),
                "context_update": {
                    "cwd": str(target),
                    "previous_cwd": str(Path(command_cwd).expanduser().resolve()),
                },
            }
        ]

    if command == "workspace":
        if not args:
            return [{"role": "result", "content": step_mod._render_workspace_commands(workspace_mode, workspace_roots)}]

        sub = args[0]
        if sub == "add":
            if len(args) != 2:
                raise ValueError("usage: /workspace add <path>")
            base = Path(command_cwd).expanduser().resolve()
            candidate = Path(args[1]).expanduser()
            target = candidate.resolve() if candidate.is_absolute() else (base / candidate).resolve()
            if not target.is_dir():
                raise ValueError(f"not a directory: {args[1]}")
            roots = list(workspace_roots)
            target_s = str(target)
            if target_s not in roots:
                roots.append(target_s)
            roots.sort()
            return [{"role": "result", "content": "\n".join(roots), "workspace_update": {"mode": workspace_mode, "roots": roots}}]

        if sub == "remove":
            if len(args) != 2:
                raise ValueError("usage: /workspace remove <path>")
            base = Path(command_cwd).expanduser().resolve()
            candidate = Path(args[1]).expanduser()
            target = candidate.resolve() if candidate.is_absolute() else (base / candidate).resolve()
            roots = [root for root in workspace_roots if root != str(target)]
            if not roots:
                roots = [str(Path.cwd().resolve())]
            roots.sort()
            return [{"role": "result", "content": "\n".join(roots), "workspace_update": {"mode": workspace_mode, "roots": roots}}]

        if sub == "reset":
            if len(args) != 1:
                raise ValueError("usage: /workspace reset")
            roots = [str(Path.cwd().resolve())]
            return [{"role": "result", "content": roots[0], "workspace_update": {"mode": "strict", "roots": roots}}]

        if sub == "mode":
            if len(args) != 2 or args[1] not in {"strict", "unbounded"}:
                raise ValueError("usage: /workspace mode strict|unbounded")
            mode = args[1]
            return [
                {
                    "role": "result",
                    "content": f"mode={mode}",
                    "workspace_update": {"mode": mode, "roots": list(workspace_roots)},
                }
            ]

        raise ValueError("usage: /workspace [add|remove|reset|mode]")

    if command == "outline":
        if args:
            raise ValueError("usage: /outline")
        return [{"role": "result", "content": step_mod._render_outline(working)}]

    if command == "compact":
        dry_run = False
        threshold = 500
        i = 0
        while i < len(args):
            arg = args[i]
            if arg == "--dry-run":
                dry_run = True
                i += 1
                continue
            if arg == "--threshold":
                if i + 1 >= len(args):
                    raise ValueError("usage: /compact [--dry-run] [--threshold <n>]")
                try:
                    threshold = int(args[i + 1])
                except ValueError as exc:
                    raise ValueError("usage: /compact [--dry-run] [--threshold <n>]") from exc
                i += 2
                continue
            raise ValueError("usage: /compact [--dry-run] [--threshold <n>]")
        if threshold < 0:
            raise ValueError("threshold must be >= 0")

        compacted, edits = step_mod._compact_result_blocks(transcript, threshold=threshold)
        if dry_run:
            if not edits:
                return [{"role": "result", "content": f"compact dry-run: no RESULT blocks above threshold={threshold}"}]
            lines = [f"compact dry-run: {len(edits)} RESULT block(s) above threshold={threshold}"]
            lines.extend(f"{edit['index']}. {edit['chars']} chars" for edit in edits)
            return [{"role": "result", "content": "\n".join(lines)}]

        if not edits:
            return [{"role": "result", "content": f"compact: no RESULT blocks above threshold={threshold}"}]
        return [
            {
                "role": "result",
                "content": f"compact: collapsed {len(edits)} RESULT block(s) above threshold={threshold}",
                "session_update": {"transcript": compacted},
            }
        ]

    if command == "extract":
        extract_selection = None
        if len(args) > 1:
            raise ValueError("usage: /extract [index]")
        if args:
            try:
                extract_selection = int(args[0])
            except ValueError as exc:
                raise ValueError("usage: /extract [index]") from exc

        target_message = None
        target_message_index = None
        for i, message in enumerate(reversed(working[:-1]), start=1):
            if message["role"] == "assistant":
                target_message = message
                target_message_index = len(working) - 1 - i + 1
                break
        if target_message is None or target_message_index is None:
            raise ValueError("no prior assistant message available for /extract")

        candidates, skipped = step_mod._extract_frontier_assistant_candidates(target_message["content"])
        if not candidates:
            if skipped:
                detail = "\n".join(skipped)
                raise ValueError(
                    "latest assistant message has no extractable callable intent\n"
                    f"skipped callable-looking blocks:\n{detail}"
                )
            raise ValueError("latest assistant message has no extractable callable intent")

        if extract_selection is None:
            lines = [
                "extract candidates from latest assistant message:",
                *[f"{i}. {candidate['kind']}\n{candidate['preview']}" for i, candidate in enumerate(candidates, start=1)],
            ]
            if skipped:
                lines.append("skipped callable-looking blocks:")
                lines.extend(skipped)
            content = (
                f"{lines[0]}\n" + "\n".join(lines[1:])
            )
            return [{"role": "result", "content": content}]

        if extract_selection < 1 or extract_selection > len(candidates):
            raise ValueError(f"index out of range: {extract_selection}")
        chosen_candidate = candidates[extract_selection - 1]
        chosen = chosen_candidate.get("adopt", chosen_candidate["preview"])
        return [{"role": "user", "content": chosen, "provenance": {"source": "adopted"}}]

    if command == "replay":
        dry_run = False
        force = False
        replay_selection: int | None = None
        i = 0
        while i < len(args):
            arg = args[i]
            if arg == "--dry-run":
                dry_run = True
                i += 1
                continue
            if arg == "--force":
                force = True
                i += 1
                continue
            if arg == "--index":
                if i + 1 >= len(args):
                    raise ValueError("usage: /replay [--dry-run] [--index <n>] [--force]")
                try:
                    replay_selection = int(args[i + 1])
                except ValueError as exc:
                    raise ValueError("usage: /replay [--dry-run] [--index <n>] [--force]") from exc
                i += 2
                continue
            raise ValueError("usage: /replay [--dry-run] [--index <n>] [--force]")

        replay_candidates: list[dict] = []
        for idx, message in enumerate(working[:-1], start=1):
            plan, ambiguous = step_mod.extract_plan_with_status(message["content"], yaml_position="any")
            if ambiguous:
                continue
            if plan is not None:
                replay_candidates.append(
                    {
                        "index": idx,
                        "kind": "tool_plan",
                        "preview": f"message #{idx} {message['role']}: tool plan",
                        "plan": plan,
                    }
                )
                continue
            if message["role"] == "assistant":
                loose_command, _ = step_mod._extract_loose_command(message["content"])
                if loose_command is not None:
                    try:
                        argv = step_mod.shlex.split(loose_command)
                    except ValueError:
                        continue
                    if argv:
                        replay_candidates.append(
                            {
                                "index": idx,
                                "kind": "assistant_loose_command",
                                "preview": f"message #{idx} assistant loose command: $ {loose_command}",
                                "plan": [{"tool_name": "shell", "args": {"argv": argv}}],
                            }
                        )

        if not replay_candidates:
            raise ValueError("no replayable callable messages found in history")

        if replay_selection is None:
            if len(replay_candidates) == 1 and not dry_run:
                only = replay_candidates[0]
                status = "already executed" if already_executed_indices and only["index"] in already_executed_indices else "not executed"
                return [
                    {
                        "role": "result",
                        "content": (
                            f"replay candidate: 1 found ({status})\n"
                            f"1. {only['preview']}\n"
                            "confirm with: /replay --index 1"
                        ),
                    }
                ]
            lines = ["replay candidates:"]
            for n, replay_candidate in enumerate(replay_candidates, start=1):
                status = (
                    "already executed"
                    if already_executed_indices and replay_candidate["index"] in already_executed_indices
                    else "not executed"
                )
                lines.append(f"{n}. {replay_candidate['preview']} [{status}]")
            lines.append("execute with: /replay --index <n>")
            return [{"role": "result", "content": "\n".join(lines)}]

        if replay_selection < 1 or replay_selection > len(replay_candidates):
            raise ValueError(f"index out of range: {replay_selection}")
        chosen = replay_candidates[replay_selection - 1]
        if already_executed_indices and chosen["index"] in already_executed_indices and not force:
            raise ValueError("target already has tool_request records; rerun with --force")

        if dry_run:
            return [
                {
                    "role": "result",
                    "content": (
                        f"replay dry-run: would execute candidate {replay_selection}\n"
                        f"{chosen['preview']}\n"
                        f"target message index: {chosen['index']}\n"
                        "execution context: current command cwd/workspace (not historical)"
                    ),
                }
            ]

        executed_nodes = step_mod._as_nodes(
            execute(
                working,
                chosen["plan"],
            )
        )
        for node in executed_nodes:
            node["replay_execution"] = {
                "target_message_index": chosen["index"],
                "request_plan": chosen["plan"],
            }
        return executed_nodes

    if command == "config":
        if not args or args[0] == "show" or (len(args) == 1 and args[0] == "--sources"):
            show_sources = False
            if args and args[0] == "--sources":
                show_sources = True
            if args and args[0] == "show":
                if len(args) == 2 and args[1] == "--sources":
                    show_sources = True
                elif len(args) > 1:
                    raise ValueError("usage: /config show [--sources]")
            elif len(args) > 1:
                raise ValueError("usage: /config [show] [--sources]")
            flat = step_mod.flatten_config(config)
            if show_sources:
                sources = config_sources or {}
                lines = [f"{k} = {flat[k]}    [source={sources.get(k, 'default')}]" for k in sorted(flat)]
            else:
                lines = [f"{k} = {v}" for k, v in flat.items()]
            lines.extend(
                [
                    "",
                    "runtime-adjustable by TOAS:",
                    "  generation.*",
                    "  extraction.*",
                    "  llm.base_url",
                    "  llm.model",
                    "  runtime.*",
                    "  shell.*",
                    "  backend.mode",
                    "",
                    "backend startup-only constraints:",
                    "  backend_startup.*",
                    "  (TOAS records these settings but backend restart/apply is separate)",
                    "",
                    "Quick edits:",
                    "  /config set generation.thinking_mode disabled",
                    "  /config set generation.thinking_mode enabled",
                    "  /config set generation.max_retries 2",
                    "  /config set generation.retry_delay_s 0.25",
                    "  /config set generation.transport_mode single_user_blob",
                    "  /config set extraction.shell_staging auto",
                    "  /config set llm.base_url http://localhost:8080/v1",
                    "  /config set llm.model qwen3.5-35b-a3b",
                    "  /config set runtime.context_budget_mode strict",
                    "  /config set runtime.streaming_mode enabled",
                    "  /config set runtime.async_runs enabled",
                    "  /config set runtime.cancellation_mode enabled",
                    "  /config set runtime.thinking_stream_mode enabled",
                    "  /config set runtime.prompt_progress_mode enabled",
                    "  /config set shell.allowed_commands echo,pwd,rg",
                    "  /config set backend.mode managed-local",
                    "  /config set backend_startup.thinking_budget_tokens 0",
                    "  /config unset llm.model",
                    "  /config restore",
                    "  /config load ./toas.toml",
                    "  /config save ./toas.toml",
                    "  /config secret set llm_api_key <value>",
                ]
            )
            return [{"role": "result", "content": "\n".join(lines)}]

        if args[0] == "secret":
            if len(args) >= 3 and args[1] == "set" and args[2] == "llm_api_key":
                if len(args) != 4:
                    raise ValueError("usage: /config secret set llm_api_key <value>")
                return [
                    {
                        "role": "result",
                        "content": "secret llm_api_key set for current runtime (non-durable)",
                        "secret_update": {"action": "set", "key": "llm_api_key", "value": args[3]},
                    }
                ]
            if len(args) == 3 and args[1] == "unset" and args[2] == "llm_api_key":
                return [
                    {
                        "role": "result",
                        "content": "secret llm_api_key unset for current runtime",
                        "secret_update": {"action": "unset", "key": "llm_api_key"},
                    }
                ]
            if len(args) == 2 and args[1] == "show":
                return [{"role": "result", "content": "secret keys: llm_api_key (redacted presence only)"}]
            raise ValueError("usage: /config secret set llm_api_key <value> | /config secret unset llm_api_key | /config secret show")

        if args[0] == "set":
            if len(args) != 3:
                raise ValueError("usage: /config set <key> <value>")
            dotted_key, raw_value = args[1], args[2]
            keys = step_mod.valid_config_keys()
            if dotted_key not in keys:
                raise ValueError(
                    f"unknown config key: {dotted_key}\n"
                    f"valid keys: {', '.join(keys)}\n"
                    "try: /config show"
                )
            try:
                new_config = step_mod.apply_dotted_override(config, dotted_key, raw_value)
            except ValueError as exc:
                details = str(exc)
                if dotted_key == "generation.thinking_mode":
                    details += (
                        "\nexample: /config set generation.thinking_mode enabled"
                    )
                if dotted_key == "generation.transport_mode":
                    details += (
                        "\nexample: /config set generation.transport_mode single_user_blob"
                    )
                raise ValueError(details) from exc
            updated = step_mod.flatten_config(new_config)
            lines = [f"{k} = {v}" for k, v in updated.items()]
            section, key = dotted_key.split(".", 1)
            nested = {section: {key: updated[dotted_key]}}
            lines.extend(
                [
                    "",
                    f"Updated {dotted_key} for this session.",
                    "Persist in project defaults by editing toas.toml.",
                    f"Revert in-session with: /config set {dotted_key} {step_mod.flatten_config(config)[dotted_key]}",
                ]
            )
            return [{"role": "result", "content": "\n".join(lines), "config_update": nested}]

        if args[0] == "backend":
            if len(args) < 2:
                raise ValueError("usage: /config backend [list|add|set|remove|capture] ...")
            sub = args[1]

            def _backend_list_dicts():
                return [
                    {
                        "id": b.id,
                        "base_url": b.base_url,
                        "model": b.model,
                        "models": list(b.models),
                        "api_key_source": b.api_key_source,
                        "api_key_ref": b.api_key_ref,
                        "tags": list(b.tags),
                        "notes": b.notes,
                    }
                    for b in config.llm.backends
                ]

            if sub == "list":
                if len(args) != 2:
                    raise ValueError("usage: /config backend list")
                if not config.llm.backends:
                    return [{"role": "result", "content": "no configured backends"}]
                lines = ["configured backends:"]
                for backend in config.llm.backends:
                    lines.append(f"- {backend.id}: {backend.base_url} (model={backend.model or '-'})")
                return [{"role": "result", "content": "\n".join(lines)}]

            if sub == "add":
                if len(args) != 4:
                    raise ValueError("usage: /config backend add <id> <base_url>")
                backend_id = args[2].strip()
                base_url = args[3].strip()
                if not backend_id or not base_url:
                    raise ValueError("backend id/base_url must be non-empty")
                backends_updated = [b for b in _backend_list_dicts() if b["id"] != backend_id]
                backends_updated.append(
                    {
                        "id": backend_id,
                        "base_url": base_url,
                        "model": "",
                        "models": [],
                        "api_key_source": "env",
                        "api_key_ref": "TOAS_LLM_API_KEY",
                        "tags": [],
                        "notes": "",
                    }
                )
                return [
                    {
                        "role": "result",
                        "content": f"added backend {backend_id}",
                        "config_update": {"llm": {"backends": backends_updated}},
                    }
                ]

            if sub == "remove":
                if len(args) != 3:
                    raise ValueError("usage: /config backend remove <id>")
                backend_id = args[2].strip()
                backends_updated = [b for b in _backend_list_dicts() if b["id"] != backend_id]
                return [
                    {
                        "role": "result",
                        "content": f"removed backend {backend_id}",
                        "config_update": {"llm": {"backends": backends_updated}},
                    }
                ]

            if sub == "set":
                if len(args) != 4:
                    raise ValueError("usage: /config backend set <id>.<field> <value>")
                backend_target = args[2]
                raw_value = args[3]
                if "." not in backend_target:
                    raise ValueError("usage: /config backend set <id>.<field> <value>")
                backend_id, field = backend_target.split(".", 1)
                backends_updated = _backend_list_dicts()
                matched = False
                for item in backends_updated:
                    if item["id"] != backend_id:
                        continue
                    if field not in {"base_url", "model", "api_key_source", "api_key_ref", "models", "notes"}:
                        raise ValueError("backend field must be one of base_url|model|api_key_source|api_key_ref|models|notes")
                    if field == "models":
                        item[field] = [part.strip() for part in raw_value.split(",") if part.strip()]
                    elif field == "api_key_source":
                        value = raw_value.strip().lower()
                        if value not in {"env", "keyring"}:
                            raise ValueError("backend api_key_source must be env|keyring")
                        item[field] = value
                    else:
                        item[field] = raw_value
                    matched = True
                    break
                if not matched:
                    raise ValueError(f"unknown backend id: {backend_id}")
                return [
                    {
                        "role": "result",
                        "content": f"updated backend {backend_id}.{field}",
                        "config_update": {"llm": {"backends": backends_updated}},
                    }
                ]

            if sub == "capture":
                if len(args) != 3:
                    raise ValueError("usage: /config backend capture <id>")
                backend_id = args[2].strip()
                settings = step_mod.Settings.from_env()
                backends_updated = [b for b in _backend_list_dicts() if b["id"] != backend_id]
                backends_updated.append(
                    {
                        "id": backend_id,
                        "base_url": settings.llm_base_url,
                        "model": settings.llm_model,
                        "models": [settings.llm_model] if settings.llm_model else [],
                        "api_key_source": "env",
                        "api_key_ref": "TOAS_LLM_API_KEY",
                        "tags": [],
                        "notes": "captured from current TOAS_LLM_* runtime",
                    }
                )
                return [
                    {
                        "role": "result",
                        "content": f"captured backend {backend_id} from current runtime",
                        "config_update": {"llm": {"backends": backends_updated}},
                    }
                ]

            raise ValueError("usage: /config backend [list|add|set|remove|capture] ...")

        if args[0] == "unset":
            if len(args) != 2:
                raise ValueError("usage: /config unset <key>")
            dotted_key = args[1]
            keys = step_mod.valid_config_keys()
            if dotted_key not in keys:
                raise ValueError(
                    f"unknown config key: {dotted_key}\n"
                    f"valid keys: {', '.join(keys)}\n"
                    "try: /config show"
                )
            lines = [
                f"Unset override for {dotted_key}.",
                "Underlying value now comes from project config or environment/defaults.",
            ]
            return [{"role": "result", "content": "\n".join(lines), "config_update": {"__op__": "unset", "key": dotted_key}}]

        if args[0] == "restore":
            if len(args) != 1:
                raise ValueError("usage: /config restore")
            return [
                {
                    "role": "result",
                    "content": "Cleared session config overrides; effective config now follows project file + env/defaults.",
                    "config_update": {"__op__": "restore"},
                }
            ]

        if args[0] == "load":
            if len(args) > 2:
                raise ValueError("usage: /config load [path]")
            path = args[1] if len(args) == 2 else "toas.toml"
            base = Path(command_cwd).expanduser().resolve()
            candidate = Path(path).expanduser()
            target = candidate.resolve() if candidate.is_absolute() else (base / candidate).resolve()
            if not target.exists():
                raise ValueError(f"config file not found: {path}")
            loaded = step_mod.load_file_config(target)
            if not loaded:
                raise ValueError(f"failed to load config from: {path}")
            return [
                {
                    "role": "result",
                    "content": f"Loaded config into session override lane from {target}",
                    "config_update": loaded,
                }
            ]

        if args[0] == "save":
            if len(args) > 2:
                raise ValueError("usage: /config save [path]")
            path = args[1] if len(args) == 2 else "toas.toml"
            return [
                {
                    "role": "result",
                    "content": f"Saved effective config to {path}",
                    "config_save": {"path": path, "flat": step_mod.flatten_config(config)},
                }
            ]

        raise ValueError("usage: /config [show] [--sources] | /config set <key> <value> | /config unset <key> | /config restore | /config load [path] | /config save [path] | /config secret ...")

    if command == "help":
        if args:
            raise ValueError("usage: /help")
        return [{"role": "result", "content": step_mod.render_session_help()}]

    raise ValueError(f"unknown command: /{command}")
