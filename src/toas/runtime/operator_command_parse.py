"""Tokenize transcript controls without consuming native Windows path separators."""

from __future__ import annotations

import shlex
import sys

_WINDOWS = sys.platform == "win32"


def split_operator_command(command: str) -> list[str]:
    """Split a control (without its slash), respecting quoted path arguments.

    On Windows, path controls use backslashes literally and quotes for spaces.
    Other controls and POSIX hosts retain the existing shell-like escaping.
    """
    words = command.split(None, 2)
    path_control = words[:1] == ["cd"] or words[:2] in (
        ["workspace", "add"], ["workspace", "remove"],
        ["config", "load"], ["config", "save"],
    )
    if not _WINDOWS or not path_control:
        return shlex.split(command)
    lexer = shlex.shlex(command, posix=True)
    lexer.whitespace_split = True
    lexer.commenters = ""
    lexer.escape = ""
    return list(lexer)
