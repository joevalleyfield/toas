import re
import shlex
from dataclasses import dataclass

import yaml

_YAML_BLOCK_RE = re.compile(r"```yaml\s*\n(.*?)\n```", re.DOTALL)
_INERT_START = "[[inert]]"
_INERT_END = "[[/inert]]"
_INERT_FENCE_START = "```inert"
_FENCE_END = "```"
_TURN_INERT_DIRECTIVE = "!inert"


@dataclass(frozen=True)
class _CommandExtraction:
    command: str | None
    recovered: bool


class _LooseCommandExtractor:
    """Three-stage extractor: block discovery -> parsed extraction -> textual recovery."""

    def __call__(self, content: str) -> _CommandExtraction:
        block = extract_yaml_tail_block(content)
        if block is None:
            return _CommandExtraction(command=None, recovered=False)

        parsed = self._parse_block(block)
        if isinstance(parsed, dict):
            direct = self._command_from_mapping(parsed)
            return _CommandExtraction(command=direct, recovered=False)

        recovered = self._recover_from_text(block)
        return _CommandExtraction(command=recovered, recovered=recovered is not None)

    @staticmethod
    def _parse_block(block: str) -> object | None:
        try:
            return yaml.safe_load(block)
        except yaml.YAMLError:
            return None

    @staticmethod
    def _command_from_mapping(parsed: dict) -> str | None:
        value = parsed.get("command")
        if not isinstance(value, str):
            value = parsed.get("cmd")
        if not isinstance(value, str):
            return None
        if "\n" in value:
            command = value.strip("\n")
        else:
            command = value.strip()
        return command or None

    @staticmethod
    def _recover_from_text(block: str) -> str | None:
        for raw_line in block.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("command:"):
                command = line[len("command:") :].strip()
                return command or None
            if line.startswith("cmd:"):
                command = line[len("cmd:") :].strip()
                return command or None
        return None


_LOOSE_COMMAND_EXTRACTOR = _LooseCommandExtractor()


def _is_inert_fence_start(marker: str) -> bool:
    if not marker.startswith("```"):
        return False
    if marker.startswith(_INERT_FENCE_START):
        return True
    lower_marker = marker.lower()
    if "inert" in lower_marker:
        return True
    if "toas-output" in lower_marker and "potency=active" not in lower_marker:
        return True
    return False


def strip_inert_regions(content: str) -> str:
    """Remove inert-marked regions from content before intent extraction."""
    depth = 0
    active_fence_ticks = 0
    nested_fence_depth = 0
    out_lines: list[str] = []
    for line in content.splitlines():
        marker = line.strip()
        if active_fence_ticks > 0:
            match = re.match(r"^`+", marker)
            if match and len(match.group(0)) >= active_fence_ticks:
                if re.fullmatch(r"`+", marker):
                    if nested_fence_depth > 0:
                        nested_fence_depth -= 1
                    else:
                        active_fence_ticks = 0
                    continue
                nested_fence_depth += 1
                continue
            continue
        if _is_inert_fence_start(marker):
            match = re.match(r"^`+", marker)
            if match:
                active_fence_ticks = len(match.group(0))
                nested_fence_depth = 0
                continue
        if marker == _INERT_START:
            depth += 1
            continue
        if marker == _INERT_END:
            if depth > 0:
                depth -= 1
            continue
        if depth == 0 and active_fence_ticks == 0:
            out_lines.append(line)
    return "\n".join(out_lines)


def has_turn_header_inert_directive(content: str) -> bool:
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        return stripped == _TURN_INERT_DIRECTIVE
    return False


def extract_yaml_blocks(content: str) -> list[str]:
    return _YAML_BLOCK_RE.findall(strip_inert_regions(content))


def extract_yaml_tail_block(content: str) -> str | None:
    blocks = extract_yaml_blocks(content)
    if not blocks:
        return None
    return blocks[-1]


def extract_yaml_tail(content: str) -> object | None:
    block = extract_yaml_tail_block(content)
    if block is None:
        return None
    return _LOOSE_COMMAND_EXTRACTOR._parse_block(block)


def extract_loose_command(content: str) -> tuple[str | None, bool]:
    extracted = _LOOSE_COMMAND_EXTRACTOR(content)
    return extracted.command, extracted.recovered


def project_loose_command_for_user(command: str) -> str:
    if "\n" in command:
        return command
    return f"$ {command}"


def extract_user_tail_shell_command(content: str) -> str | None:
    command, _complete = extract_user_tail_shell_command_with_status(content)
    return command


def extract_user_tail_shell_command_with_status(content: str) -> tuple[str | None, bool]:
    lines = strip_inert_regions(content).splitlines()
    if not lines:
        return None, False
    prompt_index = _last_shell_prompt_index(lines)
    if prompt_index is None:
        return None, False
    span, complete = _collect_shell_command_span(lines, prompt_index)
    if span is None:
        return None, False
    command = "\n".join(span)
    return (command or None), complete


def extract_user_shell_command_spans(content: str) -> list[tuple[str, bool, int]]:
    lines = strip_inert_regions(content).splitlines(keepends=True)
    if not lines:
        return []
    spans: list[tuple[str, bool, int]] = []
    cursor = 0
    index = 0
    while index < len(lines):
        raw = lines[index].rstrip("\r\n")
        if not raw.startswith("$ "):
            cursor += len(lines[index])
            index += 1
            continue
        prompt_pos = cursor
        remaining = [line.rstrip("\r\n") for line in lines[index:]]
        span, complete = _collect_shell_command_span(remaining, 0)
        if span is None:
            cursor += len(lines[index])
            index += 1
            continue
        spans.append(("\n".join(span), complete, prompt_pos))
        consumed = max(1, len(span))
        cursor += sum(len(lines[index + offset]) for offset in range(consumed) if index + offset < len(lines))
        index += consumed
    return spans


def extract_user_structured_shell_command(content: str) -> str | None:
    parsed = extract_yaml_tail(content)
    if not isinstance(parsed, dict):
        return None
    return _LOOSE_COMMAND_EXTRACTOR._command_from_mapping(parsed)


def shell_argv_from_command(command: str) -> list[str] | None:
    try:
        argv = shlex.split(command)
    except ValueError:
        return None
    return argv or None


def _last_shell_prompt_index(lines: list[str]) -> int | None:
    for index in range(len(lines) - 1, -1, -1):
        if lines[index].startswith("$ "):
            return index
    return None


def _collect_shell_command_span(lines: list[str], prompt_index: int) -> tuple[list[str] | None, bool]:
    first = lines[prompt_index][2:]
    if not first.strip():
        return None, False
    command_lines = [first]
    state = _scan_shell_line(first, _ShellScanState())
    if _shell_command_complete(state):
        return command_lines, True
    for line in lines[prompt_index + 1 :]:
        command_lines.append(line)
        state = _scan_shell_line(line, state)
        if _shell_command_complete(state):
            return command_lines, True
    return command_lines, False


@dataclass(frozen=True)
class _HeredocState:
    delimiter: str
    strip_tabs: bool = False


@dataclass(frozen=True)
class _ShellScanState:
    quote: str | None = None
    escape: bool = False
    line_continuation: bool = False
    heredoc: _HeredocState | None = None


def _shell_command_complete(state: _ShellScanState) -> bool:
    return (
        state.quote is None
        and state.heredoc is None
        and state.line_continuation is False
        and state.escape is False
    )


def _scan_shell_line(line: str, state: _ShellScanState) -> _ShellScanState:
    if state.heredoc is not None:
        marker = line.lstrip("\t") if state.heredoc.strip_tabs else line
        if marker == state.heredoc.delimiter:
            return _ShellScanState()
        return _ShellScanState(heredoc=state.heredoc)

    quote = state.quote
    escape = False
    index = 0
    while index < len(line):
        char = line[index]
        if escape:
            escape = False
            index += 1
            continue
        if quote == "'":
            if char == "'":
                quote = None
            index += 1
            continue
        if quote == '"':
            if char == "\\":
                escape = True
            elif char == '"':
                quote = None
            index += 1
            continue
        if char == "'":
            quote = "'"
            index += 1
            continue
        if char == '"':
            quote = '"'
            index += 1
            continue
        if char == "\\":
            escape = True
            index += 1
            continue
        if char == "<" and index + 1 < len(line) and line[index + 1] == "<":
            heredoc, next_index = _match_heredoc(line, index)
            if heredoc is not None:
                return _ShellScanState(quote=quote, heredoc=heredoc)
            index = next_index
            continue
        index += 1

    line_continuation = _has_trailing_unescaped_backslash(line) if quote != "'" else False
    return _ShellScanState(quote=quote, line_continuation=line_continuation)


def _match_heredoc(line: str, start: int) -> tuple[_HeredocState | None, int]:
    index = start + 2
    strip_tabs = False
    if index < len(line) and line[index] == "-":
        strip_tabs = True
        index += 1
    while index < len(line) and line[index] in " \t":
        index += 1
    if index >= len(line):
        return None, index
    if line[index] in "'\"":
        quote = line[index]
        index += 1
        end = line.find(quote, index)
        if end == -1:
            return None, len(line)
        delimiter = line[index:end]
        return _HeredocState(delimiter=delimiter, strip_tabs=strip_tabs), end + 1
    match = re.match(r"[A-Za-z0-9_]+", line[index:])
    if match is None:
        return None, index + 1
    delimiter = match.group(0)
    return _HeredocState(delimiter=delimiter, strip_tabs=strip_tabs), index + len(delimiter)


def _has_trailing_unescaped_backslash(line: str) -> bool:
    stripped = line.rstrip()
    if not stripped.endswith("\\"):
        return False
    backslashes = 0
    for char in reversed(stripped):
        if char != "\\":
            break
        backslashes += 1
    return backslashes % 2 == 1
