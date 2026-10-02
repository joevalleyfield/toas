import re
import shlex
from dataclasses import dataclass

import yaml

from ..graph import normalize_tool_plan
from ..shell_intent import (
    extract_yaml_blocks,
    project_loose_command_for_user,
    shell_argv_from_command,
    strip_inert_regions,
)
from ..tools import validate_call

_STAGED_PLAN_RE = re.compile(r"```yaml staged\s*\n(.*?)\n```", re.DOTALL)
_YAML_PLAN_RE = re.compile(r"```yaml(?: staged)?\s*\n(.*?)\n```", re.DOTALL)


@dataclass(frozen=True)
class PlanSource:
    """Normalized plan plus the authored source span for each operation."""

    plan: list[dict]
    operation_sources: tuple[str, ...]


def _source_operation_spans(body: str, parsed: object, plan: list[dict]) -> tuple[str, ...] | None:
    if isinstance(parsed, dict) and "pending_tools" in parsed and isinstance(parsed["pending_tools"], list):
        node = yaml.compose(body)
        if isinstance(node, yaml.MappingNode):
            for k, v in node.value:
                if isinstance(k, yaml.ScalarNode) and k.value == "pending_tools" and isinstance(v, yaml.SequenceNode):
                    starts = []
                    for item in v.value:
                        start = item.start_mark.index
                        starts.append(body.rfind("\n", 0, start) + 1)
                    end_pos = v.end_mark.index
                    ends = starts[1:] + [end_pos]
                    return tuple(body[s:e] for s, e in zip(starts, ends, strict=True))
    if isinstance(parsed, list):
        node = yaml.compose(body)
        if not isinstance(node, yaml.SequenceNode) or len(node.value) != len(plan):
            return None
        starts = []
        for item in node.value:
            start = item.start_mark.index
            starts.append(body.rfind("\n", 0, start) + 1)
        return tuple(body[start:end] for start, end in zip(starts, starts[1:] + [len(body)], strict=True))
    return (body,)


def extract_plan_source(
    content: str,
    *,
    plan: list[dict],
    staged: bool = False,
    source_position: int | None = None,
) -> PlanSource | None:
    """Find *plan* in a YAML fence and retain parser-validated authored spans."""
    source_view = strip_inert_regions(content)
    for match in _YAML_PLAN_RE.finditer(source_view):
        if source_position is not None and match.start() != source_position:
            continue
        is_staged = content[match.start() : match.start() + 14].startswith("```yaml staged")
        if is_staged != staged:
            continue
        body = match.group(1)
        try:
            parsed = yaml.safe_load(body)
            normalized, error = normalize_tool_plan(parsed)
            if error is not None or normalized != plan:
                continue
            spans = _source_operation_spans(body, parsed, normalized)
        except yaml.YAMLError:
            continue
        if spans is not None:
            return PlanSource(plan=normalized, operation_sources=spans)
    if not staged and (source_position is None or source_position == 0):
        try:
            parsed = yaml.safe_load(source_view)
            normalized, error = normalize_tool_plan(parsed)
            if error is None and normalized == plan:
                spans = _source_operation_spans(source_view, parsed, normalized)
                if spans is not None:
                    return PlanSource(plan=normalized, operation_sources=spans)
        except yaml.YAMLError:
            pass
    return None


def render_loose_command_preview(command: str) -> str:
    projected = project_loose_command_for_user(command)
    if "\n" in projected:
        return f"```sh\n{projected}\n```"
    return projected


def render_plan_as_yaml_preview(
    plan: list[dict],
    *,
    verbose: bool = False,
    projection_shape: str = "auto",
) -> str:
    return render_plan_preview(plan, verbose=verbose, projection_shape=projection_shape)


def render_plan_recovery(
    retry: dict,
    remainder: list[dict],
    *,
    retry_source: str | None = None,
    retry_content: str | None = None,
    retry_note: str | None = None,
    remainder_source: str | None = None,
    remainder_reference: str | None = None,
) -> str:
    retry_yaml = (retry_source if retry_source is not None else yaml.safe_dump([retry], sort_keys=False)).strip()
    rendered_retry = retry_content.strip() if retry_content is not None else f"```yaml\n{retry_yaml}\n```"
    sections = ["Retry failed operation (edit directly, then step):"]
    if retry_note is not None:
        sections.append(retry_note)
    sections.append(rendered_retry)
    if remainder_reference is not None:
        sections.extend(["Remaining referenced assistant source (bounded):", remainder_reference])
    elif remainder:
        remainder_yaml = (
            remainder_source if remainder_source is not None else yaml.safe_dump(remainder, sort_keys=False)
        ).strip()
        sections.extend(
            [
                "Remaining forward plan (staged; not yet executable):",
                f"```yaml staged\n{remainder_yaml}\n```",
            ]
        )
    return "\n\n".join(sections)


def extract_staged_plan(content: str) -> list[dict]:
    matches = _STAGED_PLAN_RE.findall(content)
    if len(matches) != 1:
        return []
    try:
        parsed = yaml.safe_load(matches[0])
    except yaml.YAMLError:
        return []
    plan, error = normalize_tool_plan(parsed)
    return plan if error is None and plan is not None else []


def _render_plan_yaml(plan: list[dict]) -> str:
    dumped = yaml.safe_dump(plan, sort_keys=False).strip()
    return f"```yaml\n{dumped}\n```"


def _compact_shell_projection(call: dict) -> str | None:
    if not isinstance(call, dict):
        return None
    tool_name = call.get("tool_name")
    args = call.get("args")
    if not isinstance(args, dict):
        return None

    if tool_name == "shell":
        argv = args.get("argv")
        if not (isinstance(argv, list) and argv and all(isinstance(part, str) and part for part in argv)):
            return None
        if len(argv) == 1 and " " in argv[0]:
            # Preserve original command text for single-token argv forms that
            # already contain spacing/quoting, instead of re-escaping via shlex.
            return project_loose_command_for_user(argv[0].strip())
        if len(argv) >= 3 and argv[0] in {"sh", "bash"} and argv[1] in {"-lc", "-c"} and isinstance(argv[2], str):
            return project_loose_command_for_user(argv[2])
        return project_loose_command_for_user(shlex.join(argv))

    if tool_name == "shell_script":
        script = args.get("script")
        if isinstance(script, str) and script.strip():
            normalized = script.strip("\n") if "\n" in script else script.strip()
            if normalized:
                return project_loose_command_for_user(normalized)
    return None


def render_compact_plan_preview(plan: list[dict]) -> str | None:
    if not plan:
        return None
    projections: list[str] = []
    for call in plan:
        projected = _compact_shell_projection(call)
        if projected is None:
            return None
        projections.append(projected)
    return "\n".join(projections)


def render_plan_preview(plan: list[dict], *, verbose: bool = False, projection_shape: str = "auto") -> str:
    if projection_shape == "yaml":
        return _render_plan_yaml(plan)
    if projection_shape == "shell":
        compact = render_compact_plan_preview(plan)
        return compact if compact is not None else _render_plan_yaml(plan)
    if not verbose:
        compact = render_compact_plan_preview(plan)
        if compact is not None:
            return compact
    return _render_plan_yaml(plan)


def assistant_loose_command_projection(loose_command: str, *, recovered: bool) -> dict:
    projected = project_loose_command_for_user(loose_command)
    if recovered:
        return {
            "role": "user",
            "content": (
                "[WARN] loose command YAML parse failed; using raw "
                "`command:` text as typed.\n\n"
                f"{projected}"
            ),
        }
    return {"role": "user", "content": projected}


def extract_user_shell_argv(command: str) -> list[str] | None:
    if "\n" in command:
        cleaned = command.strip("\n")
        return ["sh", "-lc", cleaned] if cleaned else None
    return shell_argv_from_command(command)


def extract_operator_command(content: str) -> tuple[str, list[str]] | None:
    lines = strip_inert_regions(content).rstrip().splitlines()
    if not lines:
        return None

    last_line = lines[-1].rstrip()
    if not last_line.startswith("/"):
        return None

    try:
        argv = shlex.split(last_line[1:])
    except ValueError:
        return None

    if not argv:
        return None

    return argv[0], argv[1:]


def extract_operator_commands(content: str) -> list[tuple[str, list[str]]]:
    commands: list[tuple[str, list[str]]] = []
    for raw in strip_inert_regions(content).splitlines():
        line = raw.rstrip()
        if not line or not line.startswith("/"):
            continue
        try:
            argv = shlex.split(line[1:])
        except ValueError:
            continue
        if not argv:
            continue
        commands.append((argv[0], argv[1:]))
    return commands


def extract_frontier_assistant_candidates(content: str, *, projection_shape: str = "auto") -> tuple[list[dict], list[str]]:
    candidates: list[dict] = []
    skipped: list[str] = []
    for i, block in enumerate(extract_yaml_blocks(content), start=1):
        looks_callable = any(
            token in block
            for token in ("tool_name:", "operation:", "name:", "tool:", "command:", "cmd:")
        )
        try:
            parsed = yaml.safe_load(block)
        except yaml.YAMLError as exc:
            if looks_callable:
                problem = "yaml parse error"
                mark = getattr(exc, "problem_mark", None)
                if mark is not None:
                    problem += f" at line {mark.line + 1}, column {mark.column + 1}"
                lines = [line.strip() for line in block.splitlines() if line.strip()]
                if lines:
                    snippet = lines[0]
                    if len(snippet) > 60:
                        snippet = snippet[:57] + "..."
                    problem += f" near `{snippet}`"
                # Help users recover from near-miss callable YAML without silently accepting bad syntax.
                if "argv:" in block and "[" in block and "]" in block:
                    problem += " (hint: use block list style for argv, one item per line)"
                skipped.append(f"{i}. {problem}")
            continue
        if isinstance(parsed, dict):
            command = parsed.get("command")
            if not isinstance(command, str):
                command = parsed.get("cmd")
            if isinstance(command, str) and command.strip():
                cleaned = command.strip("\n") if "\n" in command else command.strip()
                if cleaned:
                    candidates.append(
                        {
                            "kind": "assistant_loose_command",
                            "preview": render_loose_command_preview(cleaned),
                            "adopt": project_loose_command_for_user(cleaned),
                        }
                    )
                continue
        tool_plan, tool_plan_error = normalize_tool_plan(parsed)
        if tool_plan is not None:
            invalid = None
            for item in tool_plan:
                try:
                    validate_call(item)
                except RuntimeError as exc:
                    invalid = str(exc)
                    break
            if invalid is not None:
                skipped.append(f"{i}. invalid tool plan item: {invalid}")
                continue
            verbose_preview = _render_plan_yaml(tool_plan)
            preview = render_plan_preview(tool_plan, projection_shape=projection_shape)
            candidate = {"kind": "tool_plan", "preview": preview, "adopt": preview}
            candidate["preview_verbose"] = verbose_preview
            candidate["adopt_verbose"] = verbose_preview
            candidates.append(candidate)
            continue
        if looks_callable and tool_plan_error in {
            "conflicting callable keys: tool_name and operation",
            "conflicting callable keys: tool_name, operation, name, tool",
            "conflicting argument keys: args, arguments, params",
            "conflicting argument keys: args, arguments, params, parameters",
            "arguments must be a mapping",
            "conflicting intent keys: intent and intention",
            "intent must be a string",
            "conflicting shell payload keys: argv with command/cmd",
            "invalid shell command: command/cmd must be a non-empty string",
        }:
            skipped.append(f"{i}. invalid callable block: {tool_plan_error}")
            continue
        if looks_callable:
            skipped.append(f"{i}. callable-looking YAML block did not match supported shapes")
    return candidates, skipped
