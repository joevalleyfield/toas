"""Heal malformed YAML tool call candidates (indentation and outdent recovery)."""

from __future__ import annotations

import re

import yaml

OPERATION_RE = re.compile(r"^(\s*)-\s+(operation|tool_name|name|tool):")
ARGS_RE = re.compile(r"^(\s*)(arguments|args|params|intent|intention):")
SUBKEY_RE = re.compile(
    r"^(\s*)(path|search_block|replacement_block|start_line|end_line|match_mode|"
    r"expected_count|search_indent|replacement_indent|ensure_trailing_newline|"
    r"content|patch|argv|cwd|timeout_s|env|script):"
)

SCALAR_KEYS = frozenset({"search_block", "replacement_block", "content", "patch"})
DELIM_RE = re.compile(
    r"^\s*(search_block|replacement_block|content|patch|path|start_line|end_line|match_mode|"
    r"expected_count|search_indent|replacement_indent|ensure_trailing_newline|intent|intention|"
    r"operation|tool_name|name|tool|arguments|args|params|parameters|argv|cwd|timeout_s|env|script|"
    r"-\s+(operation|tool_name|name|tool))\s*:"
)


def heal_candidate_yaml(block: str) -> str | None:
    """Attempt to heal malformed candidate YAML block containing tool operations."""
    if not isinstance(block, str) or not block.strip():
        return None

    lines = block.splitlines()

    # Step 1: Normalize key nesting and alignment
    normalized_lines: list[str] = []
    in_list = False
    list_indent = 0
    in_args = False
    args_indent = 0

    for line in lines:
        stripped = line.strip()
        leading = len(line) - len(line.lstrip())

        op_match = OPERATION_RE.match(line)
        args_match = ARGS_RE.match(line)
        subkey_match = SUBKEY_RE.match(line)

        if op_match:
            in_list = True
            list_indent = len(op_match.group(1))
            in_args = False
            normalized_lines.append(line)
        elif in_list and args_match and leading <= list_indent:
            in_args = True
            args_indent = list_indent + 2
            normalized_lines.append(" " * args_indent + stripped)
        elif in_list and in_args and subkey_match and leading <= args_indent:
            normalized_lines.append(" " * (args_indent + 2) + stripped)
        elif not in_list and args_match:
            in_args = True
            args_indent = leading
            normalized_lines.append(line)
        elif not in_list and in_args and subkey_match and leading <= args_indent:
            normalized_lines.append(" " * (args_indent + 2) + stripped)
        else:
            normalized_lines.append(line)

    # Step 2: Normalize block scalars (search_block, replacement_block, content, patch)
    healed_lines: list[str] = []
    i = 0
    n = len(normalized_lines)
    while i < n:
        line = normalized_lines[i]
        key_match = re.match(r"^(\s*)([a-zA-Z0-9_]+)\s*:(.*)$", line)
        if key_match and key_match.group(2) in SCALAR_KEYS:
            key_indent_str = key_match.group(1)
            key_indent = len(key_indent_str)
            key = key_match.group(2)
            rest = key_match.group(3).strip()

            chomper = "|"
            if rest.startswith("|-"):
                chomper = "|-"
            elif rest.startswith("|+"):
                chomper = "|+"
            elif rest.startswith(">"):
                chomper = ">"

            body_lines: list[str] = []
            i += 1
            while i < n:
                curr = normalized_lines[i]
                curr_leading = len(curr) - len(curr.lstrip())
                if curr_leading <= key_indent and DELIM_RE.match(curr):
                    break
                body_lines.append(curr)
                i += 1

            non_blank_indents = [len(l) - len(l.lstrip()) for l in body_lines if l.strip()]
            if non_blank_indents:
                m = min(non_blank_indents)
                req_b = key_indent + 2
                delta = req_b - m
                shifted_body: list[str] = []
                for l in body_lines:
                    if l.strip():
                        new_indent = len(l) - len(l.lstrip()) + delta
                        shifted_body.append(" " * new_indent + l.lstrip())
                    else:
                        shifted_body.append("")
                indicator = "|2" if chomper == "|" else f"{chomper[0]}2{chomper[1:]}"
                healed_lines.append(f"{key_indent_str}{key}: {indicator}")
                healed_lines.extend(shifted_body)
            else:
                healed_lines.append(f"{key_indent_str}{key}: {chomper}")
                healed_lines.extend(body_lines)
        else:
            healed_lines.append(line)
            i += 1

    healed = "\n".join(healed_lines)
    if block.endswith("\n"):
        healed += "\n"
    try:
        yaml.safe_load(healed)
        return healed
    except yaml.YAMLError:
        return None
