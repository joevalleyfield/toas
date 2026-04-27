from __future__ import annotations

import re
from pathlib import Path

from .context_assembly import collect_lens_artifacts_from_events
from .operator_command_context import OperatorCommandContext


def _handle_prompts(args: list[str], *, step_mod) -> list[dict]:
    if len(args) > 1:
        raise ValueError("usage: /prompts [prefix]")
    content = step_mod._render_prompt_browse_commands(args[0] if args else None)
    return [{"role": "result", "content": content}]


def _handle_prompt(args: list[str], *, step_mod, context: OperatorCommandContext) -> list[dict]:
    if len(args) > 1:
        raise ValueError("usage: /prompt [ref_or_prefix]")
    if not args:
        return [{"role": "result", "content": step_mod._render_prompt_browse_commands(None)}]
    ref_or_prefix = args[0]
    exact = None
    try:
        exact = step_mod.load_prompt_ref(
            ref_or_prefix,
            policy=step_mod.generation_policy_from_config(context.config),
            capability_profile=context.config.capability_advertisement.profile,
            capability_hidden_tools=context.config.capability_advertisement.hidden_tools,
        )
    except RuntimeError:
        exact = None
    if exact is not None:
        return [{"role": "result", "content": exact}]
    content = step_mod._render_prompt_browse_commands(ref_or_prefix)
    if not content:
        raise ValueError(f"unknown prompt ref or prefix: {ref_or_prefix}")
    return [{"role": "result", "content": content}]


def _handle_backend(args: list[str], *, step_mod, context: OperatorCommandContext) -> list[dict]:
    if len(args) > 1:
        raise ValueError("usage: /backend [id]")
    available = step_mod._available_backends(context.config)
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


def _handle_model(args: list[str], *, step_mod, context: OperatorCommandContext) -> list[dict]:
    if len(args) > 1:
        raise ValueError("usage: /model [name]")
    selected_backend = step_mod.resolve_selected_backend(context.working)
    available = step_mod._available_models(context.config, selected_backend=selected_backend)
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


def _validate_env_key(key: str, *, step_mod) -> None:
    if not step_mod.re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
        raise ValueError("invalid env key")


def _handle_env(args: list[str], *, step_mod) -> list[dict]:
    if not args:
        return [{"role": "result", "content": "/env set <KEY> <VALUE>\n/env unset <KEY>"}]
    if len(args) == 3 and args[0] == "set":
        key = args[1]
        _validate_env_key(key, step_mod=step_mod)
        return [{"role": "result", "content": f"env set: {key}"}]
    if len(args) == 2 and args[0] == "unset":
        key = args[1]
        _validate_env_key(key, step_mod=step_mod)
        return [{"role": "result", "content": f"env unset: {key}"}]
    raise ValueError("usage: /env [set <KEY> <VALUE> | unset <KEY>]")


def _handle_shell_config(args: list[str], *, step_mod, context: OperatorCommandContext) -> list[dict]:
    if len(args) < 2 or args[1] == "list":
        baseline = tuple(
            sorted(
                step_mod.normalize_shell_grants(
                    context.config.shell.allowed_commands if context.config.shell.allowed_commands else step_mod.SHELL_ALLOWED
                )
            )
        )
        return [{"role": "result", "content": "config shell grants:\n" + (", ".join(baseline) if baseline else "(none)")}]

    sub = args[1]
    if sub in {"add", "remove"}:
        if len(args) != 3:
            raise ValueError(f"usage: {step_mod.SHELL_CONFIG_USAGE}")
        try:
            grant = step_mod.parse_shell_grant(args[2]).raw
        except ValueError as exc:
            raise ValueError(str(exc)) from exc
        baseline = set(
            step_mod.normalize_shell_grants(
                context.config.shell.allowed_commands if context.config.shell.allowed_commands else step_mod.SHELL_ALLOWED
            )
        )
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


def _handle_shell(args: list[str], *, step_mod, context: OperatorCommandContext) -> list[dict]:
    if args and args[0] == "config":
        return _handle_shell_config(args, step_mod=step_mod, context=context)

    if not args or args[0] == "list":
        effective, baseline, sources, transcript_added, transcript_removed = step_mod._resolve_shell_grants_with_sources(
            context.working,
            context.config,
        )
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
        effective = step_mod.resolve_effective_shell_allowed(context.working, context.config)
        return [{"role": "result", "content": f"shell grant updated: {args[0]} {grant}\neffective: {', '.join(effective)}"}]

    if len(args) == 1 and args[0] == "reset":
        effective = step_mod.resolve_effective_shell_allowed(context.working, context.config)
        return [{"role": "result", "content": f"shell grants reset to config baseline\neffective: {', '.join(effective)}"}]

    raise ValueError(f"usage: {step_mod.SHELL_USAGE}")


def _resolve_cd_target(raw_target: str, *, context: OperatorCommandContext) -> Path:
    if raw_target == "-":
        if context.previous_command_cwd is None:
            raise ValueError("no previous command cwd")
        return Path(context.previous_command_cwd).expanduser().resolve()
    base = Path(context.command_cwd).expanduser().resolve()
    candidate = Path(raw_target).expanduser()
    return candidate.resolve() if candidate.is_absolute() else (base / candidate).resolve()


def _guard_workspace_target(target: Path, raw_target: str, *, context: OperatorCommandContext) -> None:
    if not target.is_dir():
        raise ValueError(f"not a directory: {raw_target}")
    if context.workspace_mode == "strict":
        allowed = any(target == Path(root) or Path(root) in target.parents for root in context.workspace_roots)
        if not allowed:
            raise ValueError("cwd outside allowed workspace roots")


def _handle_pwd(args: list[str], *, context: OperatorCommandContext) -> list[dict]:
    if args:
        raise ValueError("usage: /pwd")
    return [{"role": "result", "content": str(Path(context.command_cwd).expanduser().resolve())}]


def _handle_cd(args: list[str], *, context: OperatorCommandContext) -> list[dict]:
    if len(args) != 1:
        raise ValueError("usage: /cd <path>|-")
    raw_target = args[0]
    target = _resolve_cd_target(raw_target, context=context)
    _guard_workspace_target(target, raw_target, context=context)
    return [
        {
            "role": "result",
            "content": str(target),
            "context_update": {
                "cwd": str(target),
                "previous_cwd": str(Path(context.command_cwd).expanduser().resolve()),
            },
        }
    ]


def _resolve_workspace_arg(path_arg: str, *, context: OperatorCommandContext) -> Path:
    base = Path(context.command_cwd).expanduser().resolve()
    candidate = Path(path_arg).expanduser()
    return candidate.resolve() if candidate.is_absolute() else (base / candidate).resolve()


def _handle_workspace(args: list[str], *, step_mod, context: OperatorCommandContext) -> list[dict]:
    if not args:
        return [{"role": "result", "content": step_mod._render_workspace_commands(context.workspace_mode, context.workspace_roots)}]

    sub = args[0]
    if sub == "add":
        if len(args) != 2:
            raise ValueError("usage: /workspace add <path>")
        target = _resolve_workspace_arg(args[1], context=context)
        if not target.is_dir():
            raise ValueError(f"not a directory: {args[1]}")
        roots = list(context.workspace_roots)
        target_s = str(target)
        if target_s not in roots:
            roots.append(target_s)
        roots.sort()
        return [{"role": "result", "content": "\n".join(roots), "workspace_update": {"mode": context.workspace_mode, "roots": roots}}]

    if sub == "remove":
        if len(args) != 2:
            raise ValueError("usage: /workspace remove <path>")
        target = _resolve_workspace_arg(args[1], context=context)
        roots = [root for root in context.workspace_roots if root != str(target)]
        if not roots:
            roots = [str(Path.cwd().resolve())]
        roots.sort()
        return [{"role": "result", "content": "\n".join(roots), "workspace_update": {"mode": context.workspace_mode, "roots": roots}}]

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
                "workspace_update": {"mode": mode, "roots": list(context.workspace_roots)},
            }
        ]

    raise ValueError("usage: /workspace [add|remove|reset|mode]")


def _handle_outline(args: list[str], *, step_mod, context: OperatorCommandContext) -> list[dict]:
    if args:
        raise ValueError("usage: /outline")
    return [{"role": "result", "content": step_mod._render_outline(context.working)}]


def _parse_compact_args(args: list[str]) -> tuple[bool, int]:
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
    return dry_run, threshold


def _handle_compact(args: list[str], *, step_mod, context: OperatorCommandContext) -> list[dict]:
    dry_run, threshold = _parse_compact_args(args)
    compacted, edits = step_mod._compact_result_blocks(context.transcript, threshold=threshold)
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


def _handle_lens(args: list[str], *, context: OperatorCommandContext) -> list[dict]:
    usage = (
        "usage: /lens [list|set <title> <distillation> <source_ids_csv> [use_when]"
        "|set --title <title> --source <ids_csv> [--source <id> ...] [--distillation <text>] [--use-when <text>]"
        "|remove <title>|reset]"
    )

    def _extract_fenced_distillation(frontier_content: str) -> str | None:
        # Use the last fenced block in the frontier message to support multiline
        # distillation authoring in the single editor surface.
        matches = re.findall(r"```[^\n]*\n(.*?)\n```", frontier_content, flags=re.DOTALL)
        if not matches:
            return None
        text = matches[-1].strip()
        return text or None

    def _parse_source_ids(value: str) -> list[str]:
        return [part.strip() for part in value.split(",") if part.strip()]

    def _parse_lens_set_args(set_args: list[str], frontier_content: str) -> tuple[str, str, list[str], str]:
        if set_args and not set_args[0].startswith("--"):
            if len(set_args) not in {3, 4}:
                raise ValueError(usage)
            title = set_args[0].strip()
            distillation = set_args[1].strip()
            source_ids = _parse_source_ids(set_args[2])
            use_when = set_args[3].strip() if len(set_args) == 4 else ""
            return title, distillation, source_ids, use_when

        title = ""
        distillation: str | None = None
        use_when = ""
        source_ids: list[str] = []
        i = 0
        while i < len(set_args):
            token = set_args[i]
            if token == "--title":
                if i + 1 >= len(set_args):
                    raise ValueError(usage)
                title = set_args[i + 1].strip()
                i += 2
                continue
            if token == "--distillation":
                if i + 1 >= len(set_args):
                    raise ValueError(usage)
                distillation = set_args[i + 1].strip()
                i += 2
                continue
            if token == "--source":
                if i + 1 >= len(set_args):
                    raise ValueError(usage)
                source_ids.extend(_parse_source_ids(set_args[i + 1]))
                i += 2
                continue
            if token == "--use-when":
                if i + 1 >= len(set_args):
                    raise ValueError(usage)
                use_when = set_args[i + 1].strip()
                i += 2
                continue
            raise ValueError(usage)

        if distillation is None:
            distillation = _extract_fenced_distillation(frontier_content)
        if distillation is None:
            distillation = ""
        return title, distillation, source_ids, use_when

    if not args or args[0] == "list":
        artifacts = collect_lens_artifacts_from_events(context.events)
        if not artifacts:
            return [{"role": "result", "content": "lens artifacts: (none)"}]
        lines = ["lens artifacts:"]
        for artifact in artifacts:
            pointers = ",".join(artifact.source_pointers) if artifact.source_pointers else "-"
            use_when = artifact.use_when or "-"
            lines.append(f"- {artifact.title}: {artifact.distillation} [sources={pointers}] [use_when={use_when}]")
        return [{"role": "result", "content": "\n".join(lines)}]

    sub = args[0]
    if sub == "set":
        frontier_content = ""
        if context.working and context.working[-1].get("role") == "user":
            content = context.working[-1].get("content")
            if isinstance(content, str):
                frontier_content = content
        title, distillation, source_ids, use_when = _parse_lens_set_args(args[1:], frontier_content)
        if not title or not distillation:
            raise ValueError(usage)
        if not source_ids:
            raise ValueError("source_ids_csv must include at least one message id")
        return [
            {
                "role": "result",
                "content": f"lens set: {title}",
                "lens_update": {
                    "action": "set",
                    "title": title,
                    "distillation": distillation,
                    "source_pointers": source_ids,
                    "use_when": use_when,
                },
            }
        ]

    if sub == "remove":
        if len(args) != 2:
            raise ValueError(usage)
        title = args[1].strip()
        if not title:
            raise ValueError(usage)
        return [{"role": "result", "content": f"lens removed: {title}", "lens_update": {"action": "remove", "title": title}}]

    if sub == "reset":
        if len(args) != 1:
            raise ValueError(usage)
        return [{"role": "result", "content": "lens artifacts reset", "lens_update": {"action": "reset"}}]

    raise ValueError(usage)


def handle_prompt_workspace_commands(
    command: str,
    args: list[str],
    *,
    step_mod,
    context: OperatorCommandContext,
) -> list[dict] | None:
    if command == "prompts":
        return _handle_prompts(args, step_mod=step_mod)
    if command == "prompt":
        return _handle_prompt(args, step_mod=step_mod, context=context)
    if command == "backend":
        return _handle_backend(args, step_mod=step_mod, context=context)
    if command == "model":
        return _handle_model(args, step_mod=step_mod, context=context)
    if command == "env":
        return _handle_env(args, step_mod=step_mod)
    if command == "shell":
        return _handle_shell(args, step_mod=step_mod, context=context)
    if command == "pwd":
        return _handle_pwd(args, context=context)
    if command == "cd":
        return _handle_cd(args, context=context)
    if command == "workspace":
        return _handle_workspace(args, step_mod=step_mod, context=context)
    if command == "outline":
        return _handle_outline(args, step_mod=step_mod, context=context)
    if command == "compact":
        return _handle_compact(args, step_mod=step_mod, context=context)
    if command == "lens":
        return _handle_lens(args, context=context)
    return None
