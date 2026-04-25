import re
import shlex
from dataclasses import dataclass

import yaml

_YAML_BLOCK_RE = re.compile(r"```yaml\s*\n(.*?)\n```", re.DOTALL)
_INERT_START = "[[inert]]"
_INERT_END = "[[/inert]]"
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


def strip_inert_regions(content: str) -> str:
    """Remove inert-marked regions from content before intent extraction."""
    depth = 0
    out_lines: list[str] = []
    for line in content.splitlines():
        marker = line.strip()
        if marker == _INERT_START:
            depth += 1
            continue
        if marker == _INERT_END:
            if depth > 0:
                depth -= 1
            continue
        if depth == 0:
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
    lines = strip_inert_regions(content).rstrip().splitlines()
    if not lines:
        return None
    last_line = lines[-1].strip()
    if not last_line.startswith("$ "):
        return None
    command = last_line[2:].strip()
    return command or None


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
