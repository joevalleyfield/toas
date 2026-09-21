from __future__ import annotations

import importlib
import json
import logging
import shlex
from pathlib import Path
from types import SimpleNamespace

from ..config import OperatorConfig, apply_overrides, config_from_discovered_paths
from ..graph import active_config_overrides
from ..transcript import (
    _lcp,
    _normalize_anchor_index,
    _normalize_bind_index,
)
from .action_plan import ActionPlan
from .frontier_resolution import (
    extract_plan_source,
    extract_staged_plan,
    render_plan_as_yaml_preview,
    render_plan_recovery,
)
from .intent_arbitration_edges import select_user_intent_candidates
from .reconciliation_handoff import (
    ReconciliationDiagnostics,
    ReconciliationHandoff,
)
from .result_nodes import make_result_node, validate_result_node

logger = logging.getLogger(__name__)

_VIRTUAL_ROOT_SENTINEL_ID = "n0"


def _append_frontier_debug(record: dict) -> None:
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("%s", json.dumps(record, ensure_ascii=True))


def _resolve_execution_dependencies(
    *,
    step_mod,
    command_cwd,
    workspace_mode,
    workspace_roots,
    config,
    generate,
    execute,
    events,
    config_sources: dict[str, str] | None = None,
    stream_stdout_enabled: bool | None = None,
):
    generate_fn = generate or (lambda _: None)
    if execute is not None:
        return generate_fn, execute

    live_config = [config]

    def execute_fn(_working, plan):
        return step_mod._execute_plan(
            plan,
            origin_role=_working[-1]["role"] if _working else "assistant",
            command_cwd=command_cwd,
            workspace_mode=workspace_mode,
            workspace_roots=workspace_roots,
            env_modifiers=step_mod.resolve_effective_env_modifiers(_working),
            shell_allowed_commands=step_mod.resolve_effective_shell_allowed(_working, live_config[0], events),
            assistant_timeout_s=live_config[0].shell.assistant_timeout_s,
            assistant_timeout_source=(config_sources or {}).get("shell.assistant_timeout_s", "default"),
            stream_stdout_enabled=(
                stream_stdout_enabled
                if stream_stdout_enabled is not None
                else step_mod.resolve_effective_shell_stream_stdout(
                    live_config[0],
                    step_mod.resolve_effective_env_modifiers(_working),
                )
            ),
        )

    execute_fn.__dict__["_toas_default_executor"] = True
    execute_fn.__dict__["_toas_live_config"] = live_config
    return generate_fn, execute_fn


def _deep_merge_config_overrides(base: dict, update: dict) -> dict:
    merged = dict(base)
    for key, value in update.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge_config_overrides(merged[key], value)
        else:
            merged[key] = value
    return merged


def _deep_delete_config_override(nested: dict, dotted_key: str) -> dict:
    result = dict(nested)
    parts = dotted_key.split(".", 1)
    if len(parts) == 1:
        result.pop(parts[0], None)
        return result
    section, remainder = parts
    value = result.get(section)
    if isinstance(value, dict):
        child = _deep_delete_config_override(value, remainder)
        if child:
            result[section] = child
        else:
            result.pop(section, None)
    return result


def _apply_live_config_update(*, config, baseline_config, overrides: dict, update: dict):
    operation = update.get("__op__")
    if operation == "restore":
        return baseline_config, {}
    if operation == "unset":
        dotted_key = update.get("key")
        if not isinstance(dotted_key, str) or not dotted_key:
            return config, overrides
        remaining = _deep_delete_config_override(overrides, dotted_key)
        return apply_overrides(baseline_config, remaining), remaining
    merged = _deep_merge_config_overrides(overrides, update)
    return apply_overrides(config, update), merged


def _collect_frontier_intents(*, step_mod, frontier, working, config, stream_stdout_enabled: bool | None = None):
    turn_inert = frontier.get("role") == "user" and step_mod._has_turn_header_inert_directive(frontier["content"])
    plan, _ = step_mod.extract_plan_with_status(
        frontier["content"],
        yaml_position=config.extraction.yaml_position,
    )
    if turn_inert:
        plan = None
    operator_command = step_mod._extract_operator_command(frontier["content"]) if config.extraction.operator_command else None
    extract_operator_commands = getattr(step_mod, "extract_operator_commands", None)
    operator_commands = (
        extract_operator_commands(frontier["content"])
        if config.extraction.operator_command and callable(extract_operator_commands)
        else ([operator_command] if operator_command is not None else [])
    )
    shell_complete = False
    if config.extraction.user_shell:
        extract_with_status = getattr(step_mod, "extract_user_tail_shell_command_with_status", None)
        if callable(extract_with_status):
            shell_command, shell_complete = extract_with_status(frontier["content"])
        else:
            shell_command = step_mod._extract_user_shell_command(frontier["content"])
            shell_complete = shell_command is not None
    else:
        shell_command = None
    if turn_inert:
        shell_command = None
        shell_complete = False
    shell_argv = (
        step_mod._extract_user_shell_argv(shell_command)
        if shell_command is not None and shell_complete
        else None
    )
    loose_command, loose_command_recovered = (
        step_mod._extract_loose_command(frontier["content"]) if config.extraction.loose_command_fallback else (None, False)
    )
    if turn_inert:
        loose_command, loose_command_recovered = (None, False)
    env_modifiers = step_mod.resolve_effective_env_modifiers(working)
    resolve_stream = getattr(step_mod, "resolve_effective_shell_stream_stdout", None)
    if stream_stdout_enabled is not None:
        resolved_stream_stdout_enabled = stream_stdout_enabled
    elif callable(resolve_stream):
        resolved_stream_stdout_enabled = resolve_stream(config, env_modifiers)
    else:
        resolved_stream_stdout_enabled = config.runtime.streaming_mode == "enabled"
    return (
        turn_inert,
        plan,
        operator_command,
        operator_commands,
        shell_command,
        shell_argv,
        loose_command,
        loose_command_recovered,
        env_modifiers,
        resolved_stream_stdout_enabled,
    )


def _select_user_intent_candidates(
    *,
    content: str,
    plan,
    operator_command,
    shell_command,
    shell_argv,
    yaml_position: str,
    arbitration_mode: str,
    include_plan_candidates: bool = True,
    operator_commands: list[tuple[str, list[str]]] | None = None,
) -> list[dict]:
    return select_user_intent_candidates(
        content=content,
        plan=plan,
        operator_command=operator_command,
        shell_command=shell_command,
        shell_argv=shell_argv,
        yaml_position=yaml_position,
        arbitration_mode=arbitration_mode,
        include_plan_candidates=include_plan_candidates,
        include_shell_candidates=shell_command is not None and shell_argv is not None,
        operator_commands=operator_commands,
    )


def _select_assistant_plan_candidates(*, content: str, plan, yaml_position: str, arbitration_mode: str) -> list[dict]:
    return select_user_intent_candidates(
        content=content,
        plan=plan,
        operator_command=None,
        shell_command=None,
        shell_argv=None,
        yaml_position=yaml_position,
        arbitration_mode=arbitration_mode,
        include_plan_candidates=True,
        include_shell_candidates=False,
    )


def _action_plan_from_candidate(*, candidate: dict, frontier: dict) -> ActionPlan:
    return ActionPlan.from_normalized_plan(
        candidate["value"],
        origin=frontier["role"],
        ingress=candidate["kind"],
        source=str(candidate["position"]) if candidate.get("position") is not None else None,
        plan_position=candidate.get("order"),
        selection_id=candidate.get("intent_id"),
        toolset=candidate.get("toolset"),
    )


def _run_user_intent_candidate(  # noqa: PLR0913
    *,
    candidate: dict,
    frontier_role: str,
    step_mod,
    consequences: list[dict],
    execute,
    events: list[dict],
    working: list[dict],
    transcript: str,
    command_cwd: str,
    previous_command_cwd,
    workspace_mode: str,
    workspace_roots: list[str],
    config,
    config_sources: dict[str, str] | None,
    already_executed_indices,
    env_modifiers: dict,
    stream_stdout_enabled: bool = True,
    arbitration_mode: str,
    frontier_content: str = "",
    generate=None,
) -> None:
    def _append_nodes(nodes: list[dict]) -> None:
        appended_nodes: list[dict] = []
        for node in nodes:
            if isinstance(node, dict) and node.get("role") == "result":
                validate_result_node(node)
            if isinstance(node, dict) and candidate["total"] > 1:
                node["intent_execution"] = {
                    "id": candidate["intent_id"],
                    "kind": candidate["kind"],
                    "order": candidate["order"],
                    "total": candidate["total"],
                    "arbitration": arbitration_mode,
                }
            appended_nodes.append(node)
        consequences.extend(appended_nodes)

    kind = candidate["kind"]
    if kind == "operator":
        command, args = candidate["value"]
        try:
            _append_nodes(
                step_mod._execute_operator_command(
                    command,
                    args,
                    execute=execute,
                    generate=generate,
                    events=events,
                    working=working,
                    transcript=transcript,
                    command_cwd=command_cwd,
                    previous_command_cwd=previous_command_cwd,
                    workspace_mode=workspace_mode,
                    workspace_roots=workspace_roots,
                    config=config,
                    config_sources=config_sources,
                    already_executed_indices=already_executed_indices,
                )
            )
        except (RuntimeError, ValueError) as exc:
            consequences.append(
                make_result_node(
                    f"[ERROR] /{command}: {exc}",
                    origin_role=frontier_role,
                    origin_kind="slash_command",
                )
            )
        return
    if kind == "plan":
        plan = candidate["value"]
        results = step_mod._execute_plan_for_frontier(
            working,
            plan,
            frontier_role="user",
            execute=execute,
            command_cwd=command_cwd,
            workspace_mode=workspace_mode,
            workspace_roots=workspace_roots,
            env_modifiers=env_modifiers,
            stream_stdout_enabled=stream_stdout_enabled,
        )
        _append_nodes(results)
        _append_plan_recovery_consequence(
            step_mod=step_mod,
            consequences=consequences,
            plan=plan,
            results=results,
            frontier_content=frontier_content,
            allow_failure_recovery=False,
        )
        return
    if kind == "shell":
        try:
            _append_nodes(
                step_mod._execute_user_shell(
                    candidate["value"],
                    origin_role=frontier_role,
                    base_cwd=command_cwd,
                    env_modifiers=env_modifiers,
                    stream_stdout_enabled=stream_stdout_enabled,
                )
            )
        except RuntimeError as exc:
            detail = str(exc)
            payload = {
                "tool_name": "shell",
                "ok": False,
                "summary": detail,
                "error": detail,
            }
            _append_nodes(
                [
                    make_result_node(
                        f"[ERROR] shell: {detail}",
                        origin_role=frontier_role,
                        origin_kind="user_shell",
                        payload=payload,
                    )
                ]
            )
        return
    if kind == "unsupported_exec":
        language = candidate["value"].get("language") or "unknown"
        reason = candidate["value"].get("reason") or "unsupported executable fence"
        _append_nodes(
            [
                make_result_node(
                    f"[ERROR] executable fence `{language} exec`: {reason}",
                    origin_role=frontier_role,
                    origin_kind="tool_call",
                )
            ]
        )
        return
    raise RuntimeError(f"unknown user intent candidate kind: {kind}")


def _build_new_transcript_nodes(
    *,
    step_mod,
    transcript: str,
    log: list[dict],
    lineage: list[dict] | None = None,
    bind_index,
    anchor_index,
    bind_parent,
    storage_tip_parent,
):
    nodes = step_mod.parse_transcript(transcript)
    # Step reconstruction is transcript/LCP authoritative.
    bind_index = _normalize_bind_index(bind_index, log)
    bound_log = log[bind_index:]
    anchor_index = _normalize_anchor_index(None, nodes, bound_log)
    i = anchor_index + _lcp(nodes[anchor_index:], bound_log[anchor_index:])
    i = _stabilize_lcp_for_assistant_tail_replay(nodes=nodes, bound_log=bound_log, lcp_index=i)
    new_from_transcript = nodes[i:]

    corrections: dict[int, str] = {}
    uncertain: set[int] = set()
    for j, node in enumerate(new_from_transcript):
        old = bound_log[i + j] if i + j < len(bound_log) else None
        if old is None or node.get("role") != "user":
            continue
        old_prov = old.get("provenance")
        if isinstance(old_prov, dict) and old_prov.get("source") == "llm_generated" and "id" in old:
            corrections[j] = old["id"]
        elif old_prov is None and old.get("role") != "user":
            uncertain.add(j)

    divergence_parent = None
    bound_lineage = (lineage or [])[bind_index:] if lineage else []
    if i == 0 and bound_lineage:
        root_id = bound_lineage[0].get("id")
        if isinstance(root_id, str) and root_id:
            divergence_parent = _VIRTUAL_ROOT_SENTINEL_ID
    elif i > 0:
        boundary_idx = _map_lcp_index_to_lineage_boundary_index(
            lcp_index=i,
            bound_log=bound_log,
            bound_lineage=bound_lineage,
        )
        if boundary_idx is None or boundary_idx < 0 or boundary_idx >= len(bound_lineage):
            boundary_id = None
        else:
            boundary_id = bound_lineage[boundary_idx].get("id")
        if isinstance(boundary_id, str) and boundary_id:
            divergence_parent = boundary_id

    new_from_transcript = step_mod._annotate_branch_parent(
        new_from_transcript,
        continuation_parent=divergence_parent,
        storage_tip_parent=None,
    )
    replayed_assistant_ids = {
        index: old["id"]
        for index, node in enumerate(new_from_transcript)
        for old in bound_log[i:]
        if node.get("role") == "assistant"
        and node.get("content") == old.get("content")
        and old.get("role") == "assistant"
        and isinstance(old.get("id"), str)
    }
    annotated = []
    for j, node in enumerate(new_from_transcript):
        if j in corrections:
            annotated.append({**node, "provenance": {"source": "user_correction", "corrects": corrections[j]}})
        elif node.get("role") == "user" and "provenance" not in node and j not in uncertain:
            annotated.append({**node, "provenance": {"source": "user_authored"}})
        elif j in replayed_assistant_ids:
            annotated.append({**node, "provenance": {"source": "assistant_restep", "restep_of": replayed_assistant_ids[j]}})
        else:
            annotated.append(node)
    _append_frontier_debug(
        {
            "phase": "build_new_transcript_nodes",
            "bind_index": bind_index,
            "anchor_index": anchor_index,
            "lcp_index": i,
            "parsed_nodes_len": len(nodes),
            "bound_log_len": len(bound_log),
            "new_from_transcript_len": len(annotated),
            "divergence_parent": divergence_parent,
            "bind_parent": None,
            "storage_tip_parent": None,
        }
    )
    diagnostics = ReconciliationDiagnostics(
        corrections=corrections,
        uncertain=uncertain,
        parsed_nodes_len=len(nodes),
        bound_log_len=len(bound_log),
        new_from_transcript_len=len(annotated),
    )
    return bind_index, i, annotated, divergence_parent, diagnostics


def _branch_shell_grant_events(working: list[dict]) -> list[dict]:
    """Project direct shell-grant declarations preceding the frontier.

    This is deliberately a narrow first reducer.  It gives a rewritten
    transcript branch its own grants without consulting unrelated journal
    records; the fuller typed control projection will replace it.
    """
    events: list[dict] = []
    for node in working[:-1]:
        content = node.get("content")
        if not isinstance(content, str):
            continue
        for line in content.splitlines():
            if not line.startswith("/shell "):
                continue
            try:
                args = shlex.split(line)[1:]
            except ValueError:
                continue
            if not args:
                continue
            action = args[0]
            if action in {"add", "allow", "remove", "deny"} and len(args) >= 2:
                scope = "session"
                if len(args) == 4 and args[2] == "--scope":
                    scope = args[3]
                if scope in {"global", "user", "workspace", "head", "session", "transient"}:
                    events.append({"kind": "shell_scope_grant", "payload": {"scope": scope, "action": "add" if action in {"add", "allow"} else "remove", "grant": args[1]}})
            elif action == "reset":
                scope = "session"
                if len(args) == 3 and args[1] == "--scope":
                    scope = args[2]
                if scope in {"global", "user", "workspace", "head", "session", "transient"}:
                    events.append({"kind": "shell_scope_grant", "payload": {"scope": scope, "action": "reset"}})
    return events


def _matching_config_load_resolution(*, declaration: list[str], events: list[dict]) -> tuple[dict | None, str | None]:
    """Find the one immutable load result proven by the same control declaration."""
    if len(declaration) >= 3 and declaration[2] == "--fresh":
        return None, "fresh config loads must be stepped at the frontier"

    source_messages = {
        event.get("id"): event
        for event in events
        if isinstance(event.get("id"), str) and isinstance(event.get("content"), str)
    }
    matches: dict[str, dict] = {}
    for event in events:
        if event.get("kind") != "config_load_resolution":
            continue
        payload = event.get("payload")
        source_id = event.get("related_to")
        source = source_messages.get(source_id)
        if not isinstance(payload, dict) or not isinstance(source, dict):
            continue
        if payload.get("reconstitution_eligible") is not True:
            continue
        delta = payload.get("delta")
        if not isinstance(delta, dict) or not delta:
            continue
        for line in source["content"].splitlines():
            if not line.startswith("/config "):
                continue
            try:
                source_declaration = shlex.split(line)
            except ValueError:
                continue
            if source_declaration != declaration:
                continue
            fingerprint = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
            matches[fingerprint] = delta
            break
    if len(matches) == 1:
        return next(iter(matches.values())), None
    if not matches:
        return None, "no immutable result matches this /config load declaration"
    return None, "multiple immutable results match this /config load declaration"


def _branch_config_from_direct_declarations(
    *, step_mod, working: list[dict], baseline_config, events: list[dict] | None = None, fail_unresolved_loads: bool = False
):
    """Reduce transcript-native config deltas and proven immutable load results."""
    config = baseline_config
    overrides: dict = {}
    applied = False
    errors: list[str] = []
    for node in working[:-1]:
        content = node.get("content")
        if not isinstance(content, str):
            continue
        for line in content.splitlines():
            if not line.startswith("/config "):
                continue
            try:
                args = shlex.split(line)
            except ValueError:
                continue
            if len(args) == 4 and args[1] == "set" and args[2] in step_mod.valid_config_keys():
                try:
                    updated = step_mod.apply_dotted_override(config, args[2], args[3])
                except ValueError:
                    continue
                value = step_mod.flatten_config(updated)[args[2]]
                section, key = args[2].split(".", 1)
                update = {section: {key: value}}
                config, overrides = _apply_live_config_update(
                    config=config,
                    baseline_config=baseline_config,
                    overrides=overrides,
                    update=update,
                )
                applied = True
            elif len(args) == 3 and args[1] == "unset" and args[2] in step_mod.valid_config_keys():
                config, overrides = _apply_live_config_update(
                    config=config,
                    baseline_config=baseline_config,
                    overrides=overrides,
                    update={"__op__": "unset", "key": args[2]},
                )
                applied = True
            elif len(args) == 2 and args[1] == "restore":
                config, overrides = _apply_live_config_update(
                    config=config,
                    baseline_config=baseline_config,
                    overrides=overrides,
                    update={"__op__": "restore"},
                )
                applied = True
            elif args[1] == "load" and (len(args) in {2, 3} or (len(args) == 4 and args[2] == "--fresh")):
                update, error = _matching_config_load_resolution(declaration=args, events=events or [])
                if update is None:
                    if fail_unresolved_loads and error is not None:
                        errors.append(error)
                    continue
                config, overrides = _apply_live_config_update(
                    config=config,
                    baseline_config=baseline_config,
                    overrides=overrides,
                    update=update,
                )
                applied = True
    return config, applied, errors


def _branch_command_context_from_direct_declarations(
    *,
    working: list[dict],
    command_cwd: str,
    previous_command_cwd: str | None,
    workspace_mode: str,
    workspace_roots: list[str],
) -> tuple[str, str | None, bool]:
    """Reduce valid direct `/cd` declarations before the current frontier."""
    from .operator_command_prompt_workspace import _guard_workspace_target, _resolve_cd_target

    cwd = command_cwd
    previous_cwd = previous_command_cwd
    applied = False
    for node in working[:-1]:
        content = node.get("content")
        if not isinstance(content, str):
            continue
        for line in content.splitlines():
            if not line.startswith("/cd "):
                continue
            try:
                args = shlex.split(line[1:])
            except ValueError:
                continue
            if len(args) != 2 or args[0] != "cd":
                continue
            context = SimpleNamespace(
                command_cwd=cwd,
                previous_command_cwd=previous_cwd,
                workspace_mode=workspace_mode,
                workspace_roots=workspace_roots,
            )
            try:
                target = _resolve_cd_target(args[1], context=context)
                _guard_workspace_target(target, args[1], context=context)
            except ValueError:
                continue
            previous_cwd = str(Path(cwd).expanduser().resolve())
            cwd = str(target)
            applied = True
    return cwd, previous_cwd, applied


def _branch_workspace_scope_from_direct_declarations(
    *,
    working: list[dict],
    baseline_mode: str,
    baseline_roots: list[str],
) -> tuple[str, list[str], bool]:
    """Reduce direct `/workspace` declarations before the current frontier."""
    mode = baseline_mode
    roots = list(baseline_roots)
    applied = False
    for node in working[:-1]:
        content = node.get("content")
        if not isinstance(content, str):
            continue
        for line in content.splitlines():
            if not line.startswith("/workspace "):
                continue
            try:
                args = shlex.split(line[1:])
            except ValueError:
                continue
            if len(args) == 3 and args[1] in {"add", "remove"}:
                target = Path(args[2]).expanduser().resolve()
                if not target.is_dir():
                    continue
                target_s = str(target)
                if args[1] == "add" and target_s not in roots:
                    roots.append(target_s)
                elif args[1] == "remove":
                    roots = [root for root in roots if root != target_s] or list(baseline_roots)
                roots.sort()
                applied = True
            elif len(args) == 2 and args[1] == "reset":
                mode, roots, applied = "strict", list(baseline_roots), True
            elif len(args) == 3 and args[1] == "mode" and args[2] in {"strict", "unbounded"}:
                mode, applied = args[2], True
    return mode, roots, applied



def _stabilize_lcp_for_assistant_tail_replay(*, nodes: list[dict], bound_log: list[dict], lcp_index: int) -> int:
    """Prevent n-1 fallback when only terminal assistant replay text drifts.

    This protects transcript-first progression for the observed sequence:
    step without append -> append replayed consequence -> repeated append.
    """
    if lcp_index < 0:
        return lcp_index
    if len(nodes) != len(bound_log):
        return lcp_index
    if not nodes or not bound_log:
        return lcp_index
    if lcp_index != len(nodes) - 1:
        return lcp_index
    tail_node = nodes[-1]
    tail_bound = bound_log[-1]
    tail_role = tail_node.get("role")
    if tail_role != "assistant" or tail_role != tail_bound.get("role"):
        return lcp_index
    tail_content = str(tail_node.get("content", ""))
    bound_content = str(tail_bound.get("content", ""))
    if "## RESULT" not in tail_content and "## RESULT" not in bound_content:
        return lcp_index
    # If all prior messages remain identical and only the final body differs,
    # keep full frontier alignment to avoid reusing n-1.
    for left, right in zip(nodes[:-1], bound_log[:-1], strict=False):
        if left.get("role") != right.get("role") or left.get("content") != right.get("content"):
            return lcp_index
    return len(nodes)


def _map_lcp_index_to_lineage_boundary_index(
    *,
    lcp_index: int,
    bound_log: list[dict] | None = None,
    bound_lineage: list[dict] | None = None,
) -> int | None:
    """Map transcript/message-space LCP index to bound-lineage boundary index."""
    if lcp_index <= 0:
        return None
    # Keep translation explicit in one seam; current policy is trivial i-1.
    return lcp_index - 1


def _execute_frontier_consequences(  # noqa: PLR0913
    *,
    step_mod,
    events: list[dict],
    working: list[dict],
    transcript: str,
    execute,
    generate,
    command_cwd: str,
    previous_command_cwd,
    workspace_mode: str,
    workspace_roots: list[str],
    config,
    config_sources: dict[str, str] | None,
    already_executed_indices,
    stream_stdout_enabled: bool | None = None,
    baseline_config=None,
):
    consequences: list[dict] = []
    should_return_early = False
    if not working:
        return consequences, should_return_early
    frontier = working[-1]
    (
        turn_inert,
        plan,
        operator_command,
        operator_commands,
        shell_command,
        shell_argv,
        loose_command,
        loose_command_recovered,
        env_modifiers,
        stream_stdout_enabled,
    ) = _collect_frontier_intents(
        step_mod=step_mod,
        frontier=frontier,
        working=working,
        config=config,
        stream_stdout_enabled=stream_stdout_enabled,
    )
    should_return_early = _route_frontier_consequence_path(
        step_mod=step_mod,
        frontier=frontier,
        consequences=consequences,
        plan=plan,
        operator_command=operator_command,
        operator_commands=operator_commands,
        shell_command=shell_command,
        shell_argv=shell_argv,
        loose_command=loose_command,
        loose_command_recovered=loose_command_recovered,
        turn_inert=turn_inert,
        execute=execute,
        events=events,
        working=working,
        transcript=transcript,
        command_cwd=command_cwd,
        previous_command_cwd=previous_command_cwd,
        workspace_mode=workspace_mode,
        workspace_roots=workspace_roots,
        config=config,
        config_sources=config_sources,
        already_executed_indices=already_executed_indices,
        env_modifiers=env_modifiers,
        stream_stdout_enabled=stream_stdout_enabled,
        generate=generate,
        baseline_config=baseline_config,
    )
    return consequences, should_return_early


def _working_with_transcript_tail_frontier(*, transcript_nodes: list[dict], reconstructed_working: list[dict]) -> list[dict]:
    """Use transcript tail as the only frontier candidate."""
    transcript_tail = transcript_nodes[-1] if transcript_nodes else None
    if transcript_tail is None:
        return reconstructed_working
    if not reconstructed_working:
        return [transcript_tail]
    return reconstructed_working[:-1] + [transcript_tail]


def _route_frontier_consequence_path(  # noqa: PLR0913
    *,
    step_mod,
    frontier: dict,
    consequences: list[dict],
    plan,
    operator_command,
    operator_commands,
    shell_command,
    shell_argv,
    loose_command,
    loose_command_recovered: bool,
    turn_inert: bool,
    execute,
    events: list[dict],
    working: list[dict],
    transcript: str,
    command_cwd: str,
    previous_command_cwd,
    workspace_mode: str,
    workspace_roots: list[str],
    config,
    config_sources: dict[str, str] | None,
    already_executed_indices,
    env_modifiers,
    stream_stdout_enabled: bool,
    generate,
    baseline_config=None,
) -> bool:
    if _should_project_assistant_single_shell(step_mod=step_mod, frontier=frontier, loose_command=loose_command, plan=plan):
        consequences.append(step_mod._assistant_loose_command_projection(loose_command, recovered=loose_command_recovered))
        return False
    if frontier["role"] in {"user", "control"}:
        should_return_early = _handle_user_or_control_frontier(
            step_mod=step_mod,
            frontier=frontier,
            consequences=consequences,
            plan=plan,
            operator_command=operator_command,
            operator_commands=operator_commands,
            shell_command=shell_command,
            shell_argv=shell_argv,
            turn_inert=turn_inert,
            execute=execute,
            events=events,
            working=working,
            transcript=transcript,
            command_cwd=command_cwd,
            previous_command_cwd=previous_command_cwd,
            workspace_mode=workspace_mode,
            workspace_roots=workspace_roots,
            config=config,
            config_sources=config_sources,
            already_executed_indices=already_executed_indices,
            env_modifiers=env_modifiers,
            stream_stdout_enabled=stream_stdout_enabled,
            generate=generate,
            baseline_config=baseline_config,
        )
        if _should_return_after_user_or_control(consequences):
            return should_return_early
        return False
    arbitration_mode = getattr(config.extraction, "intent_arbitration", "in_order")
    assistant_candidates = _select_assistant_plan_candidates(
        content=frontier["content"],
        plan=plan,
        yaml_position=config.extraction.yaml_position,
        arbitration_mode=arbitration_mode,
    ) if frontier["role"] == "assistant" and not turn_inert else []
    if assistant_candidates:
        unsupported = [candidate for candidate in assistant_candidates if candidate["kind"] == "unsupported_exec"]
        for candidate in unsupported:
            language = candidate["value"].get("language") or "unknown"
            reason = candidate["value"].get("reason") or "unsupported executable fence"
            consequences.append(
                make_result_node(
                    f"[ERROR] executable fence `{language} exec`: {reason}",
                    origin_role="assistant",
                    origin_kind="tool_call",
                )
            )
        assistant_candidates = [candidate for candidate in assistant_candidates if candidate["kind"] != "unsupported_exec"]
        if not assistant_candidates:
            return False
        if _append_strict_assistant_plan_error_if_needed(
            step_mod=step_mod,
            consequences=consequences,
            candidates=assistant_candidates,
            arbitration_mode=arbitration_mode,
        ):
            return False
        for candidate in assistant_candidates:
            _handle_plan_frontier(
                step_mod=step_mod,
                frontier=frontier,
                consequences=consequences,
                working=working,
                plan=candidate["value"],
                action_plan=_action_plan_from_candidate(candidate=candidate, frontier=frontier),
                execute=execute,
                command_cwd=command_cwd,
                workspace_mode=workspace_mode,
                workspace_roots=workspace_roots,
                env_modifiers=env_modifiers,
                stream_stdout_enabled=stream_stdout_enabled,
                config=config,
            )
        return False
    if plan is not None:
        _handle_plan_frontier(
            step_mod=step_mod,
            frontier=frontier,
            consequences=consequences,
            working=working,
            plan=plan,
            execute=execute,
            command_cwd=command_cwd,
            workspace_mode=workspace_mode,
            workspace_roots=workspace_roots,
            env_modifiers=env_modifiers,
            stream_stdout_enabled=stream_stdout_enabled,
            config=config,
        )
        return False
    if frontier["role"] == "assistant":
        consequences.append(
            _handle_assistant_non_plan_frontier(
                step_mod=step_mod,
                loose_command=loose_command,
                loose_command_recovered=loose_command_recovered,
            )
        )
    return False


def _should_project_assistant_single_shell(*, step_mod, frontier: dict, loose_command, plan) -> bool:
    return (
        frontier["role"] == "assistant"
        and loose_command is not None
        and plan is not None
        and step_mod._plan_is_single_shell(plan)
    )


def _should_return_after_user_or_control(consequences: list[dict]) -> bool:
    return bool(consequences)


def _handle_plan_frontier(  # noqa: PLR0913
    *,
    step_mod,
    frontier: dict,
    consequences: list[dict],
    working: list[dict],
    plan,
    execute,
    command_cwd: str,
    workspace_mode: str,
    workspace_roots: list[str],
    env_modifiers,
    stream_stdout_enabled: bool,
    config,
    action_plan: ActionPlan | None = None,
) -> None:
    if action_plan is not None:
        plan = action_plan.as_normalized_plan()
    results = _execute_plan_frontier_results(
        step_mod=step_mod,
        working=working,
        plan=plan,
        frontier_role=frontier["role"],
        execute=execute,
        command_cwd=command_cwd,
        workspace_mode=workspace_mode,
        workspace_roots=workspace_roots,
        env_modifiers=env_modifiers,
        stream_stdout_enabled=stream_stdout_enabled,
    )
    _append_plan_frontier_results(consequences=consequences, results=results)
    assistant_shell_authorization = (
        frontier["role"] == "assistant"
        and len(plan) == 1
        and step_mod._plan_contains_shell(plan)
        and step_mod._assistant_results_include_shell_block(results)
    )
    recovery_staged = False
    if not assistant_shell_authorization:
        recovery_staged = _append_plan_recovery_consequence(
            step_mod=step_mod,
            consequences=consequences,
            plan=plan,
            results=results,
            frontier_content=frontier["content"],
            allow_failure_recovery=frontier["role"] != "user",
        )
    if recovery_staged:
        return
    repair_frontier = _build_plan_repair_frontier(results=results, plan_size=len(plan))
    if repair_frontier is not None:
        consequences.append(repair_frontier)
    if _should_auto_stage_assistant_shell_block(
        step_mod=step_mod,
        frontier_role=frontier["role"],
        plan=plan,
        results=results,
        config=config,
    ):
        consequences.append(_build_assistant_auto_staged_plan(step_mod=step_mod, plan=plan, config=config))


def _execute_plan_frontier_results(  # noqa: PLR0913
    *,
    step_mod,
    working: list[dict],
    plan,
    frontier_role: str,
    execute,
    command_cwd: str,
    workspace_mode: str,
    workspace_roots: list[str],
    env_modifiers,
    stream_stdout_enabled: bool,
) -> list[dict]:
    return step_mod._execute_plan_for_frontier(
        working,
        plan,
        frontier_role=frontier_role,
        execute=execute,
        command_cwd=command_cwd,
        workspace_mode=workspace_mode,
        workspace_roots=workspace_roots,
        env_modifiers=env_modifiers,
        stream_stdout_enabled=stream_stdout_enabled,
    )


def _append_plan_frontier_results(*, consequences: list[dict], results: list[dict]) -> None:
    consequences.extend(results)


def _failed_result_index(results: list[dict]) -> int | None:
    for index, result in enumerate(results):
        payload = result.get("payload")
        if isinstance(payload, dict) and payload.get("ok") is False:
            return index
    return None


def _is_completed_shell_result(result: dict) -> bool:
    payload = result.get("payload")
    return (
        isinstance(payload, dict)
        and payload.get("tool_name") in {"shell", "shell_script"}
        and type(payload.get("exit_code")) is int
    )


def _append_plan_recovery_consequence(
    *,
    step_mod,
    consequences: list[dict],
    plan: list[dict],
    results: list[dict],
    frontier_content: str,
    retry_source: str | None = None,
    retry_content: str | None = None,
    retry_note: str | None = None,
    remainder_reference: str | None = None,
    recovery_provenance: dict | None = None,
    allow_failure_recovery: bool = True,
) -> bool:
    failed_index = _failed_result_index(results)
    staged_remainder = extract_staged_plan(frontier_content)
    if failed_index is not None:
        if not allow_failure_recovery:
            return False
        if _is_completed_shell_result(results[failed_index]):
            return False
        source = extract_plan_source(frontier_content, plan=plan)
        if source is not None:
            failed_source = source.operation_sources[failed_index]
            remainder_source = "".join(source.operation_sources[failed_index + 1 :])
        else:
            failed_source = None
            remainder_source = None
        remainder = staged_remainder if len(plan) == 1 and staged_remainder else plan[failed_index + 1 :]
        if len(plan) == 1 and staged_remainder:
            staged_source = extract_plan_source(frontier_content, plan=staged_remainder, staged=True)
            remainder_source = (
                "".join(staged_source.operation_sources) if staged_source is not None else remainder_source
            )
        consequences.append(
            {
                "role": "user",
                "content": render_plan_recovery(
                    plan[failed_index],
                    remainder,
                    retry_source=retry_source if retry_source is not None else failed_source,
                    retry_content=retry_content,
                    retry_note=retry_note,
                    remainder_source=remainder_source,
                    remainder_reference=remainder_reference,
                ),
                "provenance": {"source": "adopted", **(recovery_provenance or {})},
                "recovery_transition": "frontier",
            }
        )
        return True
    if staged_remainder:
        staged_source = extract_plan_source(frontier_content, plan=staged_remainder, staged=True)
        consequences.append(
            {
                "role": "user",
                "content": (
                    f"```yaml\n{''.join(staged_source.operation_sources).strip()}\n```"
                    if staged_source is not None
                    else render_plan_as_yaml_preview(staged_remainder, projection_shape="yaml")
                ),
                "provenance": {"source": "adopted"},
            }
        )
        return True
    return False


def _repair_command_arg(*, result: dict, operation_index: int | None = None) -> str | None:
    suggestion = result.get("repair_suggestion")
    if not isinstance(suggestion, dict):
        payload = result.get("payload")
        if isinstance(payload, dict):
            suggestion = payload.get("repair_suggestion")
    if not isinstance(suggestion, dict):
        return None
    if suggestion.get("type") != "frontier_repair":
        return None
    tool_name = suggestion.get("tool_name")
    args_patch = suggestion.get("args_patch")
    if tool_name != "replace_block" or not isinstance(args_patch, dict):
        return None
    search_indent = args_patch.get("search_indent")
    if set(args_patch) != {"search_indent"} or not isinstance(search_indent, int) or search_indent < 0:
        return None
    prefix = f"{operation_index}:" if operation_index is not None else ""
    return f"{prefix}search_indent={search_indent}"


def _build_repair_frontier(*, result: dict) -> dict | None:
    command_arg = _repair_command_arg(result=result)
    if command_arg is None:
        return None
    return {
        "role": "user",
        "content": f"/heal {command_arg}",
        "provenance": {"source": "adopted"},
    }


def _build_plan_repair_frontier(*, results: list[dict], plan_size: int) -> dict | None:
    indexed = plan_size > 1
    command_args = [
        command_arg
        for index, result in enumerate(results, start=1)
        if (command_arg := _repair_command_arg(result=result, operation_index=index if indexed else None)) is not None
    ]
    if not command_args:
        return None
    return {
        "role": "user",
        "content": f"/heal {' '.join(command_args)}",
        "provenance": {"source": "adopted"},
    }


def _should_auto_stage_assistant_shell_block(*, step_mod, frontier_role: str, plan, results: list[dict], config) -> bool:
    has_shell = step_mod._plan_contains_shell(plan)
    auto_stage = config.extraction.shell_staging == "auto"
    blocked_shell = step_mod._assistant_results_include_shell_block(results)
    return frontier_role == "assistant" and has_shell and auto_stage and blocked_shell


def _handle_assistant_non_plan_frontier(*, step_mod, loose_command, loose_command_recovered: bool) -> dict:
    if loose_command is not None:
        return step_mod._assistant_loose_command_projection(loose_command, recovered=loose_command_recovered)
    return {
        "role": "user",
        "content": "",
        "metadata": {"transient_projection": "frontier_flip"},
    }


def _build_assistant_auto_staged_plan(*, step_mod, plan, config) -> dict:
    staged_content = step_mod._render_plan_as_yaml_preview(
        plan,
        projection_shape=getattr(config.extraction, "projection_shape", "auto"),
    )
    staged_plan, _ = step_mod.extract_plan_with_status(
        staged_content,
        yaml_position=config.extraction.yaml_position,
    )
    staged_shell_command = step_mod._extract_user_shell_command(staged_content)
    if staged_plan is None and staged_shell_command is None:
        staged_content = step_mod._render_plan_as_yaml_preview(plan, verbose=True)
    return {
        "role": "user",
        "content": staged_content,
        "provenance": {"source": "adopted"},
    }


def _handle_user_or_control_frontier(  # noqa: PLR0913
    *,
    step_mod,
    frontier: dict,
    consequences: list[dict],
    plan,
    operator_command,
    operator_commands,
    shell_command,
    shell_argv,
    turn_inert: bool,
    execute,
    events: list[dict],
    working: list[dict],
    transcript: str,
    command_cwd: str,
    previous_command_cwd,
    workspace_mode: str,
    workspace_roots: list[str],
    config,
    config_sources: dict[str, str] | None,
    already_executed_indices,
    env_modifiers,
    stream_stdout_enabled: bool,
    generate,
    baseline_config=None,
) -> bool:
    arbitration_mode = getattr(config.extraction, "intent_arbitration", "in_order")
    candidates = _select_user_intent_candidates(
        content=frontier["content"],
        plan=plan,
        operator_command=operator_command,
        shell_command=shell_command,
        shell_argv=shell_argv,
        yaml_position=config.extraction.yaml_position,
        arbitration_mode=arbitration_mode,
        include_plan_candidates=not turn_inert,
    )
    candidates = _expand_in_order_operator_candidates(
        candidates=candidates,
        operator_commands=operator_commands,
        arbitration_mode=arbitration_mode,
    )
    if _append_strict_mixed_intent_error_if_needed(
        step_mod=step_mod,
        consequences=consequences,
        candidates=candidates,
        arbitration_mode=arbitration_mode,
    ):
        return False
    live_overrides = active_config_overrides(events)
    for candidate in candidates:
        consequence_start = len(consequences)
        _run_user_intent_candidate(
            candidate=candidate,
            frontier_role=frontier["role"],
            step_mod=step_mod,
            consequences=consequences,
            execute=execute,
            events=events,
            working=working,
            transcript=transcript,
            command_cwd=command_cwd,
            previous_command_cwd=previous_command_cwd,
            workspace_mode=workspace_mode,
            workspace_roots=workspace_roots,
            config=config,
            config_sources=config_sources,
            already_executed_indices=already_executed_indices,
            env_modifiers=env_modifiers,
            stream_stdout_enabled=stream_stdout_enabled,
            arbitration_mode=arbitration_mode,
            frontier_content=frontier["content"],
            generate=generate,
        )
        for node in consequences[consequence_start:]:
            config_update = node.get("config_update") if isinstance(node, dict) else None
            if isinstance(config_update, dict):
                config, live_overrides = _apply_live_config_update(
                    config=config,
                    baseline_config=baseline_config or config,
                    overrides=live_overrides,
                    update=config_update,
                )
                live_config = getattr(execute, "__dict__", {}).get("_toas_live_config")
                if isinstance(live_config, list):
                    live_config[0] = config
        if any(
            isinstance(node, dict) and node.get("recovery_transition") == "frontier"
            for node in consequences[consequence_start:]
        ):
            break
    return _handle_user_generation_fallback(
        step_mod=step_mod,
        frontier=frontier,
        consequences=consequences,
        candidates=candidates,
        working=working,
        config=config,
        generate=generate,
    )


def _expand_in_order_operator_candidates(*, candidates: list[dict], operator_commands: list, arbitration_mode: str) -> list[dict]:
    if arbitration_mode != "in_order" or not operator_commands:
        return candidates
    kinds = {candidate.get("kind") for candidate in candidates}
    if not kinds <= {"operator"}:
        return candidates
    return [
        {
            "kind": "operator",
            "value": command_tuple,
            "order": idx + 1,
            "total": len(operator_commands),
            "intent_id": idx + 1,
        }
        for idx, command_tuple in enumerate(operator_commands)
    ]


def _append_strict_mixed_intent_error_if_needed(*, step_mod=None, consequences: list[dict], candidates: list[dict], arbitration_mode: str) -> bool:
    if arbitration_mode != "strict" or len(candidates) <= 1:
        return False
    handles = ", ".join(f"#{candidate['intent_id']}:{candidate['kind']}" for candidate in candidates)
    consequences.append(
        make_result_node(
            (
                f"[ERROR] mixed-intent strict mode: {len(candidates)} intents detected; "
                "resolve to one intent or change extraction.intent_arbitration\n"
                f"detected intents: {handles}"
            ),
            origin_role="user",
            origin_kind="tool_call",
        )
    )
    return True


def _append_strict_assistant_plan_error_if_needed(*, step_mod=None, consequences: list[dict], candidates: list[dict], arbitration_mode: str) -> bool:
    if arbitration_mode != "strict" or len(candidates) <= 1:
        return False
    handles = ", ".join(f"#{candidate['intent_id']}:{candidate['kind']}" for candidate in candidates)
    consequences.append(
        make_result_node(
            (
                f"[ERROR] assistant strict mode: {len(candidates)} callable groups detected; "
                "resolve to one group or change extraction.intent_arbitration\n"
                f"detected groups: {handles}"
            ),
            origin_role="assistant",
            origin_kind="tool_call",
        )
    )
    return True


def _handle_user_generation_fallback(*, step_mod, frontier: dict, consequences: list[dict], candidates: list[dict], working: list[dict], config, generate) -> bool:
    if candidates or frontier["role"] != "user":
        return False
    guarded = step_mod._generation_guard_result(working=working, config=config)
    if guarded is not None:
        consequences.append(guarded)
        return True
    consequences.extend(step_mod._as_nodes(generate(working)))
    return False


def _build_bootstrap_node(*, step_mod, config) -> dict:
    bootstrap_content = step_mod.load_prompt_ref(
        config.session.bootstrap_prompt_ref,
        mode=config.prompt.mode,
        constraints=list(config.prompt.constraints),
        policy=step_mod.generation_policy_from_config(config),
        capability_profile=config.capability_advertisement.profile,
        capability_hidden_tools=config.capability_advertisement.hidden_tools,
        prompt_ingress=config.prompt.ingress,
        prompt_output_profile=config.prompt.output_profile,
    )
    return {
        "role": "user",
        "content": bootstrap_content,
        "provenance": {"source": "bootstrap_seed"},
    }


def _bootstrap_seed_consequences(*, step_mod, config) -> tuple[list[dict], list[dict]]:
    bootstrap_node = _build_bootstrap_node(step_mod=step_mod, config=config)
    next_user_slot = {"role": "user", "content": "", "provenance": {"source": "bootstrap_seed"}}
    return [bootstrap_node], [bootstrap_node, next_user_slot]


def _build_run_step_frontier_context(*, step_mod, transcript: str, log: list[dict], bind_index: int = 0) -> ReconciliationHandoff:
    bind_index, lcp_index, new_from_transcript, divergence_parent, diagnostics = _build_new_transcript_nodes(
        step_mod=step_mod,
        transcript=transcript,
        log=log,
        lineage=log,
        bind_index=bind_index,
        anchor_index=None,
        bind_parent=None,
        storage_tip_parent=None,
    )
    reconstructed_working = log[bind_index : bind_index + lcp_index] + new_from_transcript
    transcript_nodes = step_mod.parse_transcript(transcript)
    working_for_frontier = _working_with_transcript_tail_frontier(
        transcript_nodes=transcript_nodes,
        reconstructed_working=reconstructed_working,
    )
    frontier = working_for_frontier[-1] if working_for_frontier else None
    handoff = ReconciliationHandoff(
        working_for_frontier=working_for_frontier,
        new_from_transcript=new_from_transcript,
        frontier=frontier if isinstance(frontier, dict) else None,
        divergence_parent=divergence_parent,
        bind_index=bind_index,
        lcp_index=lcp_index,
        diagnostics=diagnostics,
    )
    _log_run_step_frontier_context(handoff, log=log)
    return handoff



def _preview_content(node: dict | None) -> str | None:
    if not isinstance(node, dict) or not node.get("content"):
        return None
    return str(node.get("content", ""))[:160]


def _log_run_step_frontier_context(handoff: ReconciliationHandoff, *, log: list[dict]) -> None:
    lineage_tail = log[-1] if log else None
    lcp_lineage_tail = log[handoff.lcp_index - 1] if handoff.lcp_index > 0 and handoff.lcp_index - 1 < len(log) else None
    frontier = handoff.frontier
    _append_frontier_debug(
        {
            "phase": "run_step_frontier",
            "log_len": len(log),
            "working_len": len(handoff.working_for_frontier),
            "bind_index": handoff.bind_index,
            "lcp_index": handoff.lcp_index,
            "divergence_parent": handoff.divergence_parent,
            "frontier_role": frontier.get("role") if isinstance(frontier, dict) else None,
            "frontier_id": frontier.get("id") if isinstance(frontier, dict) else None,
            "frontier_preview": _preview_content(frontier),
            "lineage_tail_id": lineage_tail.get("id") if isinstance(lineage_tail, dict) else None,
            "lineage_tail_role": lineage_tail.get("role") if isinstance(lineage_tail, dict) else None,
            "lineage_tail_preview": _preview_content(lineage_tail),
            "lcp_lineage_tail_id": lcp_lineage_tail.get("id") if isinstance(lcp_lineage_tail, dict) else None,
            "lcp_lineage_tail_role": lcp_lineage_tail.get("role") if isinstance(lcp_lineage_tail, dict) else None,
            "lcp_lineage_tail_preview": _preview_content(lcp_lineage_tail),
        }
    )


def run_step(  # noqa: PLR0913
    transcript: str,
    log: list[dict],
    generate=None,
    execute=None,
    command_cwd=".",
    previous_command_cwd=None,
    workspace_mode="strict",
    workspace_roots=None,
    config=None,
    config_sources: dict[str, str] | None = None,
    already_executed_indices=None,
    events: list[dict] | None = None,
    stream_stdout_enabled: bool | None = None,
    bind_index: int = 0,
    injected_control: bool = False,
):
    step_mod = importlib.import_module("toas.step")

    workspace_roots = workspace_roots or [str(Path.cwd().resolve())]
    config = config or OperatorConfig()
    durable_events = events if events is not None else log
    baseline_config = config_from_discovered_paths(workdir=Path(command_cwd).expanduser().resolve())

    handoff = _build_run_step_frontier_context(
        step_mod=step_mod,
        transcript=transcript,
        log=log,
        bind_index=bind_index,
    )

    # A branch rewrite must not inherit unrelated journal grants.  The direct
    # declarations in the reconstructed transcript are the Phase-1 policy
    # projection; linear callers retain the legacy durable-event fallback.
    is_rewrite = not injected_control and handoff.lcp_index < len(log) - handoff.bind_index
    branch_grant_events = _branch_shell_grant_events(handoff.working_for_frontier)
    branch_config, branch_config_present, branch_config_errors = _branch_config_from_direct_declarations(
        step_mod=step_mod,
        working=handoff.working_for_frontier,
        baseline_config=baseline_config,
        events=durable_events,
        fail_unresolved_loads=is_rewrite,
    )
    workspace_baseline_mode = "strict" if is_rewrite else workspace_mode
    workspace_baseline_roots = [str(Path.cwd().resolve())] if is_rewrite else workspace_roots
    workspace_mode, workspace_roots, _branch_workspace_present = _branch_workspace_scope_from_direct_declarations(
        working=handoff.working_for_frontier,
        baseline_mode=workspace_baseline_mode,
        baseline_roots=workspace_baseline_roots,
    )
    context_baseline_cwd = str(Path.cwd().resolve()) if is_rewrite else command_cwd
    context_baseline_previous_cwd = None if is_rewrite else previous_command_cwd
    command_cwd, previous_command_cwd, _branch_context_present = _branch_command_context_from_direct_declarations(
        working=handoff.working_for_frontier,
        command_cwd=context_baseline_cwd,
        previous_command_cwd=context_baseline_previous_cwd,
        workspace_mode=workspace_mode,
        workspace_roots=workspace_roots,
    )
    # CLI-injected `control=` turns are intentionally ephemeral transcript
    # input.  They materialize as sibling control records, rather than edits
    # to session.md, so their LCP with the selected message lineage is not a
    # user-authored transcript rewrite.  Preserve their existing
    # history-forward configuration lane.
    if is_rewrite or branch_config_present:
        config = branch_config
    if branch_config_errors:
        consequences = [
            make_result_node(
                f"[ERROR] config load reconstitution: {branch_config_errors[0]}",
                origin_role="control",
                origin_kind="slash_command",
            )
        ]
        return handoff.new_from_transcript + consequences, consequences
    policy_events = durable_events if not is_rewrite and not branch_grant_events else branch_grant_events
    generate, execute = _resolve_execution_dependencies(
        step_mod=step_mod,
        command_cwd=command_cwd,
        workspace_mode=workspace_mode,
        workspace_roots=workspace_roots,
        config=config,
        generate=generate,
        execute=execute,
        events=policy_events,
        config_sources=config_sources,
        stream_stdout_enabled=stream_stdout_enabled,
    )

    if not handoff.working_for_frontier and config.session.bootstrap_prompt_ref:
        return _bootstrap_seed_consequences(step_mod=step_mod, config=config)

    callable_intent_present = _frontier_has_callable_intent(
        step_mod=step_mod,
        frontier=handoff.frontier,
        working=handoff.working_for_frontier,
        config=config,
    )
    callable_near_miss_error = _frontier_callable_near_miss_error(
        step_mod=step_mod,
        frontier=handoff.frontier,
        config=config,
    )
    if callable_near_miss_error and not callable_intent_present:
        consequences = [
            make_result_node(
                callable_near_miss_error,
                origin_role=handoff.frontier["role"] if isinstance(handoff.frontier, dict) else "user",
                origin_kind="tool_call",
            )
        ]
        return handoff.new_from_transcript + consequences, consequences
    consequences, should_return_early = _execute_frontier_consequences(
        step_mod=step_mod,
        events=durable_events,
        working=handoff.working_for_frontier,
        transcript=transcript,
        execute=execute,
        generate=generate,
        command_cwd=command_cwd,
        previous_command_cwd=previous_command_cwd,
        workspace_mode=workspace_mode,
        workspace_roots=workspace_roots,
        config=config,
        config_sources=config_sources,
        already_executed_indices=already_executed_indices,
        stream_stdout_enabled=stream_stdout_enabled,
        baseline_config=baseline_config,
    )
    if callable_intent_present and not consequences:
        _append_frontier_debug(
            {
                "phase": "run_step_callable_guard",
                "error": "callable frontier produced no consequences",
                "frontier_role": handoff.frontier.get("role") if isinstance(handoff.frontier, dict) else None,
                "frontier_preview": (
                    str(handoff.frontier.get("content", ""))[:160]
                    if isinstance(handoff.frontier, dict) and handoff.frontier.get("content")
                    else None
                ),
                "log_len": len(log),
                "working_len": len(handoff.working_for_frontier),
                "lcp_index": handoff.lcp_index,
            }
        )
        raise RuntimeError("callable frontier produced no consequences")
    if should_return_early:
        return handoff.new_from_transcript + consequences, consequences

    return handoff.new_from_transcript + consequences, consequences



def _frontier_has_callable_intent(*, step_mod, frontier: dict | None, working: list[dict], config) -> bool:
    if not isinstance(frontier, dict):
        return False
    (
        _turn_inert,
        plan,
        operator_command,
        _operator_commands,
        shell_command,
        shell_argv,
        loose_command,
        _loose_command_recovered,
        _env_modifiers,
        _stream_stdout_enabled,
    ) = _collect_frontier_intents(step_mod=step_mod, frontier=frontier, working=working, config=config)
    return any(
        (
            plan is not None,
            operator_command is not None,
            shell_command is not None,
            shell_argv is not None,
            loose_command is not None,
        )
    )


def _frontier_callable_near_miss_error(*, step_mod, frontier: dict | None, config) -> str | None:
    if not isinstance(frontier, dict) or frontier.get("role") != "assistant":
        return None
    content = str(frontier.get("content", ""))
    if not content:
        return None
    looks_callable = any(token in content for token in ("operation:", "tool_name:", "command:", "cmd:"))
    if not looks_callable:
        return None
    extractor = getattr(step_mod, "_extract_frontier_assistant_candidates", None)
    if not callable(extractor):
        return None
    candidates, skipped = extractor(content, projection_shape=getattr(config.extraction, "projection_shape", "auto"))
    if candidates or not skipped:
        return None
    first = skipped[0]
    if "yaml parse error" not in first:
        return None
    return "[ERROR] callable-looking assistant block is not valid YAML for extraction\n" + first
