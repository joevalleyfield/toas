import re
import shlex

import yaml

_YAML_BLOCK_RE = re.compile(r"```yaml\s*\n(.*?)\n```", re.DOTALL)


def extract_yaml_blocks(content: str) -> list[str]:
    return _YAML_BLOCK_RE.findall(content)


def extract_yaml_tail_block(content: str) -> str | None:
    blocks = extract_yaml_blocks(content)
    if not blocks:
        return None
    return blocks[-1]


def extract_yaml_tail(content: str) -> object | None:
    block = extract_yaml_tail_block(content)
    if block is None:
        return None
    try:
        return yaml.safe_load(block)
    except yaml.YAMLError:
        return None


def extract_loose_command(content: str) -> tuple[str | None, bool]:
    parsed = extract_yaml_tail(content)
    if not isinstance(parsed, dict):
        block = extract_yaml_tail_block(content)
        if block is None:
            return None, False
        for raw_line in block.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("command:"):
                command = line[len("command:") :].strip()
                return command or None, True
            if line.startswith("cmd:"):
                command = line[len("cmd:") :].strip()
                return command or None, True
        return None, False

    value = parsed.get("command")
    if not isinstance(value, str):
        value = parsed.get("cmd")
    if not isinstance(value, str):
        return None, False

    if "\n" in value:
        command = value.strip("\n")
    else:
        command = value.strip()
    return command or None, False


def project_loose_command_for_user(command: str) -> str:
    if "\n" in command:
        return command
    return f"$ {command}"


def extract_user_tail_shell_command(content: str) -> str | None:
    lines = content.rstrip().splitlines()
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


def shell_argv_from_command(command: str) -> list[str] | None:
    try:
        argv = shlex.split(command)
    except ValueError:
        return None
    return argv or None

