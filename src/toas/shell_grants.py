from __future__ import annotations

import fnmatch
import re
import shlex
from dataclasses import dataclass

_EXACT_RE = re.compile(r"^[A-Za-z0-9._+-]+$")
_PREFIX_RE = re.compile(r"^[A-Za-z0-9._+-]+$")


@dataclass(frozen=True)
class ShellGrant:
    raw: str
    kind: str
    pattern: str


def parse_shell_grant(raw: str) -> ShellGrant:
    text = raw.strip()
    if not text:
        raise ValueError("empty grant")
    if text.startswith("prefix:"):
        pattern = text[len("prefix:") :].strip()
        if not pattern or not _PREFIX_RE.fullmatch(pattern):
            raise ValueError("invalid prefix grant; expected prefix:<token>")
        return ShellGrant(raw=f"prefix:{pattern}", kind="prefix", pattern=pattern)
    if text.startswith("glob:"):
        pattern = text[len("glob:") :].strip()
        if not pattern:
            raise ValueError("invalid glob grant; expected glob:<pattern>")
        return ShellGrant(raw=f"glob:{pattern}", kind="glob", pattern=pattern)
    if not _EXACT_RE.fullmatch(text):
        raise ValueError("invalid exact grant; expected [A-Za-z0-9._+-]+")
    return ShellGrant(raw=text, kind="exact", pattern=text)


def normalize_shell_grants(raw_grants: list[str] | tuple[str, ...] | set[str]) -> tuple[str, ...]:
    normalized: list[str] = []
    for raw in raw_grants:
        if not isinstance(raw, str):
            continue
        grant = parse_shell_grant(raw)
        if grant.raw not in normalized:
            normalized.append(grant.raw)
    return tuple(normalized)


def shell_command_allowed(command: str, grants: list[str] | tuple[str, ...] | set[str]) -> bool:
    for raw in grants:
        grant = parse_shell_grant(raw)
        if grant.kind == "exact" and command == grant.pattern:
            return True
        if grant.kind == "prefix" and command.startswith(grant.pattern):
            return True
        if grant.kind == "glob" and fnmatch.fnmatchcase(command, grant.pattern):
            return True
    return False


def shell_script_segment_commands(script: str) -> list[str]:
    stripped = script.strip()
    if not stripped:
        return []

    lexer = shlex.shlex(stripped, posix=True, punctuation_chars="|&;")
    lexer.whitespace_split = True
    lexer.commenters = "#"
    tokens = list(lexer)
    if not tokens:
        return []

    operators = {"|", "||", "&&", ";"}
    commands: list[str] = []
    expect_command = True
    for token in tokens:
        if token in operators:
            expect_command = True
            continue
        if expect_command:
            commands.append(token)
            expect_command = False
    return commands
