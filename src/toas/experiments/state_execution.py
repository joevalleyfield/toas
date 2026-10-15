"""Paired explicit-state versus history-plus-state repository experiment.

This is an experimental runner, deliberately independent of TOAS step semantics.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from ..llm import NO_THINKING, Settings, complete_chat_response
from ..runtime.shell_runtime import configured_shell_runtime
from ..tools_cluster.shell_ops import shell_launcher_argv

SOURCE_ROOT = Path(__file__).resolve().parents[3]
PROCEDURE = """Organize all supplied dirty changes into coherent commits using the supplied repository customs. Preserve intended content and keep each task file with its change; maintain WORKBOARD references at every commit boundary. A task's WORKBOARD entry must not appear until its task file is committed; include the task file and its board update together. WORKBOARD entries are Markdown bullets exactly like `- task-slug`; preserve existing bullets when editing. Include each task's source, test, task file, and matching WORKBOARD update in its behavior commit. An empty jj working-copy commit is normal and clean; do not abandon it. Use explicit progress memory and do not repeat a tool call when its observation has not changed. State-only requests do not include prior observations: put important findings and completed work in state. Before finish, verify the working copy is clean and history is correct.

Quick jj reference: `jj status` checks the working copy; `jj diff --git` shows the complete patch; `jj log -n 5` shows recent history. The commit tool performs a focused `jj split -m "type(scope): summary" path...` for the selected paths. After a commit, jj creates a new empty working copy at `@`; that is clean. Verify the previous commit with `jj diff --git -r @-` or `jj show --git @-`. Never run `jj abandon @` to clean up an empty working copy.

Tools: inspect is one call that reports jj status, the complete patch from jj diff --git, and the last five commits; use it instead of separate scripts for status/diff/history. read returns a named file. write replaces a named existing file with complete text, using {\"type\":\"write\",\"path\":\"README.md\",\"content\":\"complete file text\"}. commit selects one or more relative paths and a description. script runs a Python or Bash snippet from the fixture; each snippet is safety-reviewed after proposal and before execution, and is rejected if no reviewer approves it. Use exactly {\"type\":\"script\",\"language\":\"bash\",\"snippet\":\"jj status\"} for Bash or replace bash with python. Scripts are general-purpose and are not an OS sandbox: do not access paths outside the fixture, use the network, or perform destructive host operations. Use the focused repository tools when they suffice.

On each inference return exactly one JSON object with state_patch and action, and no extra fields. action may be one tool call, a terminal outcome, or a plan of 1 to 8 tool calls. After inspect has exposed the full changes, prefer a short plan when remaining paths, contents, and order are already clear; this saves inference turns. The controller executes planned calls in order, records each result, and stops on the first failure. Plans receive no intermediate model feedback; group calls only when their arguments are grounded in current evidence. A plan contains only inspect, read, write, commit, or script calls. Do not put finish, blocked, or continue in a plan. A commit may contain multiple paths. Examples: {\"state_patch\":{},\"action\":{\"type\":\"inspect\"}} and {\"state_patch\":{},\"action\":{\"type\":\"plan\",\"steps\":[{\"type\":\"inspect\"},{\"type\":\"read\",\"path\":\"README.md\"}]}}. Script steps use {\"type\":\"script\",\"language\":\"bash\",\"snippet\":\"jj status\"}. Inspect the patch and read relevant files before choosing commit partitions. Keep progress updates to facts established by prior observations; update state again after receiving the plan results."""
SCHEMA_GUIDANCE = "State fields: goal (objective string); progress (concrete completed actions and findings that may matter later); next_steps (only remaining actionable work); artifacts (produced paths); blockers (obstacles preventing progress); notes (object with constraints, accepted_decisions, pending_proposals, uncertainties arrays). State-only calls receive no previous tool output except facts preserved here. Record completed progress only after observing its result. This generic state shape is authored for this experiment, not supplied by the paper."
INITIAL_STATE: dict[str, Any] = {
    "goal": "Organize two unrelated dirty changes into coherent commits under the supplied customs.",
    "progress": [],
    "next_steps": [
        "inspect changes",
        "commit documentation task",
        "commit behavior task",
        "verify clean history",
    ],
    "artifacts": [],
    "blockers": [],
    "notes": {
        "constraints": ["preserve all changes", "do not expose controller expectations"],
        "accepted_decisions": [],
        "pending_proposals": [],
        "uncertainties": [],
    },
}
CUSTOMS = "Use conventional lowercase commit descriptions: `docs(scope): summary` for documentation, `feat(scope): summary` for a new capability, and `fix(scope): summary` for a repair. Each task change includes all relevant source/test files, its task file, and matching WORKBOARD entry in the same commit. The WORKBOARD is a Markdown bullet list with one `- task-slug` entry per line; preserve existing bullets. Do not add a WORKBOARD task entry before its task file is committed. jj quick reference: `jj status`, `jj diff --git`, `jj log -n 5`; the commit tool runs focused `jj split -m \"type(scope): summary\" path...`; a new empty `@` after commit is clean; inspect the previous commit with `jj diff --git -r @-` or `jj show --git @-`. Never run `jj abandon @` to clean up an empty working copy."


class Adapter(Protocol):
    name: str
    model: str

    def call(self, messages: list[dict[str, str]], *, params: dict[str, Any]) -> dict[str, Any]: ...


def _ensure_external_root(path: Path) -> Path:
    root = path.resolve()
    if root == SOURCE_ROOT or SOURCE_ROOT in root.parents:
        raise ValueError("experiment roots must be outside the TOAS source checkout")
    return root


@dataclass
class ScriptedAdapter:
    responses: list[str]
    name: str = "scripted"
    model: str = "offline-script"
    captured: list[dict[str, Any]] = field(default_factory=list)

    def call(self, messages: list[dict[str, str]], *, params: dict[str, Any]) -> dict[str, Any]:
        self.captured.append({"messages": copy.deepcopy(messages), "params": copy.deepcopy(params)})
        if not self.responses:
            raise RuntimeError("script exhausted")
        return {
            "content": self.responses.pop(0),
            "usage": None,
            "duration_ms": 0,
            "model": self.model,
        }


@dataclass
class LiveAdapter:
    settings: Settings
    name: str = "live"
    captured: list[dict[str, Any]] = field(default_factory=list)

    @property
    def model(self) -> str:
        return self.settings.llm_model

    @property
    def manifest(self) -> dict[str, Any]:
        return {
            "provider": self.settings.llm_provider,
            "model": self.settings.llm_model,
            "configured_model": self.settings.llm_model,
            "transport_mode": self.settings.llm_transport_mode,
            "stream_mode": self.settings.llm_stream_mode,
            "thinking": "disabled",
            "decoding": "provider defaults; max_tokens supplied per call",
        }

    completion: Any = complete_chat_response

    def call(self, messages: list[dict[str, str]], *, params: dict[str, Any]) -> dict[str, Any]:
        # Pass a fresh, stateless request. Never pass prior-response/thread IDs.
        self.captured.append(
            {
                "messages": copy.deepcopy(messages),
                "params": {**copy.deepcopy(params), "extra_body": copy.deepcopy(NO_THINKING)},
            }
        )
        return self.completion(
            messages,
            settings=self.settings,
            extra_body=NO_THINKING,
            max_tokens=params.get("max_tokens"),
        )


def apply_patch(state: dict[str, Any], patch: object) -> dict[str, Any]:
    if not isinstance(patch, dict):
        raise ValueError("state_patch must be an object")

    def merge(dst: dict[str, Any], src: dict[str, Any]) -> dict[str, Any]:
        out = copy.deepcopy(dst)
        for key, value in src.items():
            if not isinstance(key, str):
                raise ValueError("patch keys must be strings")
            if value is None:
                out.pop(key, None)
            elif isinstance(value, dict) and isinstance(out.get(key), dict):
                out[key] = merge(out[key], value)
            else:
                out[key] = copy.deepcopy(value)
        return out

    candidate = merge(state, patch)
    required = {"goal", "progress", "next_steps", "artifacts", "blockers", "notes"}
    if not required <= candidate.keys():
        raise ValueError("candidate state missing required fields")
    if not isinstance(candidate["goal"], str) or not all(
        isinstance(candidate[k], list) for k in required - {"goal", "notes"}
    ):
        raise ValueError("candidate state has invalid field types")
    if not isinstance(candidate["notes"], dict) or not all(
        isinstance(candidate["notes"].get(k), list)
        for k in ("constraints", "accepted_decisions", "pending_proposals", "uncertainties")
    ):
        raise ValueError("candidate state has invalid notes categories")
    return candidate


def parse_proposal(text: str) -> dict[str, Any]:
    candidate = text.strip()
    if candidate.startswith("```") and candidate.endswith("```"):
        candidate = candidate[3:-3].strip()
        if candidate[:4].casefold() == "json":
            candidate = candidate[4:].lstrip()
    try:
        obj = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise ValueError(f"response is not JSON: {exc.msg}") from exc
    if not isinstance(obj, dict) or set(obj) != {"state_patch", "action"}:
        raise ValueError("response must contain exactly state_patch and action")
    action = obj["action"]
    if not isinstance(action, dict):
        raise ValueError("invalid action")
    if action.get("type") == "plan":
        steps = action.get("steps")
        if not isinstance(steps, list) or not 1 <= len(steps) <= 8:
            raise ValueError("plan requires 1 to 8 tool calls")
        for step in steps:
            if not isinstance(step, dict) or step.get("type") not in {
                "inspect",
                "read",
                "write",
                "commit",
                "script",
            }:
                raise ValueError("plan steps must be inspect, read, write, commit, or script calls")
    elif action.get("type") not in {
        "inspect",
        "read",
        "write",
        "commit",
        "script",
        "continue",
        "finish",
        "blocked",
    }:
        raise ValueError("invalid action")
    return obj


def _env(root: Path) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "JJ_CONFIG": str(root / "jj-config.toml"),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": str(root / "gitconfig"),
            "GIT_AUTHOR_NAME": "Harness",
            "GIT_AUTHOR_EMAIL": "harness@example.invalid",
            "GIT_COMMITTER_NAME": "Harness",
            "GIT_COMMITTER_EMAIL": "harness@example.invalid",
            "JJ_USER": "Harness",
            "JJ_EMAIL": "harness@example.invalid",
            "GIT_TERMINAL_PROMPT": "0",
        }
    )
    env.pop("JJ_EDITOR", None)
    return env


def _script_env(root: Path) -> dict[str, str]:
    """Expose a small fixture-oriented environment, not caller credentials."""
    home = root / ".experiment-home"
    temp = root / ".experiment-tmp"
    home.mkdir(exist_ok=True)
    temp.mkdir(exist_ok=True)
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(home),
        "TMPDIR": str(temp),
        "LANG": os.environ.get("LANG", "C.UTF-8"),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": str(root / "gitconfig"),
        "GIT_AUTHOR_NAME": "Harness",
        "GIT_AUTHOR_EMAIL": "harness@example.invalid",
        "GIT_COMMITTER_NAME": "Harness",
        "GIT_COMMITTER_EMAIL": "harness@example.invalid",
        "JJ_CONFIG": str(root / "jj-config.toml"),
        "JJ_USER": "Harness",
        "JJ_EMAIL": "harness@example.invalid",
        "GIT_TERMINAL_PROMPT": "0",
    }
    return env


def _run(root: Path, args: list[str], *, timeout: float = 10) -> str:
    exe = shutil.which(args[0])
    if not exe:
        raise RuntimeError(
            "jj executable is required for the repository experiment; install jj or run pure unit tests"
        )
    p = subprocess.run(
        [exe, *args[1:]], cwd=root, env=_env(root), capture_output=True, text=True, timeout=timeout
    )
    if p.returncode:
        raise RuntimeError(
            f"{args[0]} {' '.join(args[1:])} failed: {p.stderr.strip() or p.stdout.strip()}"
        )
    return p.stdout.strip()


def create_fixture(root: Path) -> dict[str, Any]:
    root = _ensure_external_root(root)
    if sys.platform == "win32" and len(str(root / ".jj/repo/op_store/operations" / ("0" * 128))) >= 260:
        raise ValueError("jj fixture path exceeds the Windows path limit; choose a shorter --output directory")
    root.mkdir(parents=True, exist_ok=True)
    (root / "AGENTS.md").write_text(
        "Use conventional commits. Keep each task's task file and matching WORKBOARD reference in its commit.\n\n"
        "Quick jj reference: `jj status` checks the working copy; `jj diff --git` shows the patch; `jj log -n 5` shows recent history. The commit tool performs `jj split -m \"type(scope): summary\" path...`. After a commit, jj creates a new empty working copy at `@`; that is clean. Verify the previous commit with `jj diff --git -r @-` or `jj show --git @-`. Never run `jj abandon @` to clean up an empty working copy.\n",
        encoding="utf-8",
    )
    (root / "tasks/open").mkdir(parents=True, exist_ok=True)
    (root / "docs").mkdir(exist_ok=True)
    (root / "src").mkdir(exist_ok=True)
    (root / "tests").mkdir(exist_ok=True)
    files = {
        "README.md": "# Demo project\n\nStable baseline.\n",
        "src/math.py": "def add(a, b):\n    return a + b\n",
        "tests/test_math.py": "from src.math import add\n\ndef test_add():\n    assert add(1, 2) == 3\n",
        "docs/guide.md": "# Guide\n\nOriginal guidance.\n",
    }
    for name, content in files.items():
        (root / name).write_text(content, encoding="utf-8")
    _run(root, ["jj", "git", "init"])
    _run(root, ["jj", "describe", "-m", "chore: baseline"])
    _run(root, ["jj", "new"])
    (root / "docs/guide.md").write_text(
        "# Guide\n\nDocument the supported operation.\n", encoding="utf-8"
    )
    (root / "tasks/open/docs-guide.md").write_text(
        "Filed as: docs-guide\n\nDocument the supported operation.\n", encoding="utf-8"
    )
    (root / "src/math.py").write_text(
        "def add(a, b):\n    return a + b\n\ndef subtract(a, b):\n    return a - b\n",
        encoding="utf-8",
    )
    (root / "tests/test_math.py").write_text(
        "from src.math import add, subtract\n\ndef test_add():\n    assert add(1, 2) == 3\n\ndef test_subtract():\n    assert subtract(3, 1) == 2\n",
        encoding="utf-8",
    )
    (root / "tasks/open/subtract.md").write_text(
        "Filed as: subtract\n\nAdd and test subtraction.\n", encoding="utf-8"
    )
    (root / "tasks/WORKBOARD.md").write_text("- docs-guide\n", encoding="utf-8")
    expected = {
        p.relative_to(root).as_posix(): p.read_text(encoding="utf-8")
        for p in root.rglob("*")
        if p.is_file() and ".git" not in p.parts and ".jj" not in p.parts
    }
    expected["tasks/WORKBOARD.md"] = "- docs-guide\n- subtract\n"
    return {
        "expected_files": expected,
        "partitions": [
            {
                "paths": ["docs/guide.md", "tasks/open/docs-guide.md", "tasks/WORKBOARD.md"],
                "prefix": "docs(",
            },
            {
                "paths": [
                    "src/math.py",
                    "tests/test_math.py",
                    "tasks/open/subtract.md",
                    "tasks/WORKBOARD.md",
                ],
                "prefix": "feat(",
            },
        ],
        "customs": CUSTOMS,
    }


def safe_path(root: Path, rel: str) -> Path:
    candidate = (root / rel).resolve()
    base = root.resolve()
    if candidate == base or base not in candidate.parents:
        raise ValueError("path escapes fixture root")
    return candidate


def _bash_command(root: Path, content: str) -> list[str]:
    configured = configured_shell_runtime(root)
    if configured:
        return shell_launcher_argv(content, runtime=list(configured))
    if sys.platform == "win32":
        command = shell_launcher_argv(content, workdir=root)
        if Path(command[0]).stem.lower() == "bash":
            return [shutil.which(command[0]) or command[0], *command[1:]]
    else:
        bash = shutil.which("bash")
        if bash:
            return [bash, "-c", content]
    raise RuntimeError("Bash runtime unavailable; configure runtime.shell_runtime with a Bash argv prefix")


def act(
    root: Path,
    action: dict[str, Any],
    *,
    timeout: float,
    review_script: Callable[[Path, dict[str, Any]], tuple[bool, str]] | None = None,
    review_records: list[dict[str, Any]] | None = None,
) -> str:
    root = _ensure_external_root(root)
    typ = action["type"]
    if typ in {"continue", "finish", "blocked"}:
        return ""
    if typ == "inspect":
        return (
            _run(root, ["jj", "status"])
            + "\n"
            + _run(root, ["jj", "diff", "--git"])
            + "\n"
            + _run(root, ["jj", "log", "-n", "5"])
        )
    if typ == "read":
        rel = action.get("path")
        if not isinstance(rel, str):
            raise ValueError("read requires a relative path")
        p = safe_path(root, rel)
        if p.is_symlink() or not p.is_file():
            raise ValueError("read target must be a regular fixture file")
        return p.read_text(encoding="utf-8")
    if typ == "write":
        rel = action.get("path")
        content = action.get("content", action.get("text"))
        if not isinstance(rel, str) or not isinstance(content, str):
            raise ValueError("write requires path and complete text content")
        p = safe_path(root, rel)
        if p.is_symlink() or not p.is_file():
            raise ValueError("write target must be an existing regular fixture file")
        p.write_text(content, encoding="utf-8")
        return f"Updated {rel} ({len(content)} characters)."
    if typ == "script":
        language = action.get("language")
        content = next(
            (
                action[key]
                for key in ("snippet", "content", "code", "command")
                if isinstance(action.get(key), str)
            ),
            None,
        )
        if language not in {"python", "bash"} or not isinstance(content, str):
            raise ValueError("script requires language python or bash and a snippet string")
        record: dict[str, Any] = {"action": copy.deepcopy(action), "approved": False}
        if review_script is None:
            record["reason"] = "No script reviewer supplied; rejected by default."
        else:
            approved, reason = review_script(root, copy.deepcopy(action))
            record.update({"approved": bool(approved), "reason": str(reason)})
        if review_records is not None:
            review_records.append(record)
        if not record["approved"]:
            raise PermissionError(record["reason"] or "Script rejected by reviewer.")
        cwd_value = action.get("cwd", ".")
        if not isinstance(cwd_value, str):
            raise ValueError("script cwd must be a relative path")
        cwd = root.resolve() if cwd_value == "." else safe_path(root, cwd_value)
        if cwd.is_symlink() or not cwd.is_dir():
            raise ValueError("script cwd must be a fixture directory")
        command = [sys.executable, "-c", content] if language == "python" else _bash_command(root, content)
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=_script_env(root),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if completed.returncode:
            raise RuntimeError(
                f"script exited {completed.returncode}; stdout={completed.stdout!r}; "
                f"stderr={completed.stderr!r}"
            )
        return json.dumps(
            {
                "language": language,
                "cwd": cwd.relative_to(root).as_posix() or ".",
                "exit_code": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            },
            ensure_ascii=False,
        )
    if typ == "commit":
        paths = action.get("paths")
        description = action.get("description")
        if (
            not isinstance(paths, list)
            or not paths
            or not all(isinstance(p, str) for p in paths)
            or not isinstance(description, str)
        ):
            raise ValueError("commit requires paths and description")
        for rel in paths:
            safe_path(root, rel)
        _run(root, ["jj", "split", "-m", description, *paths], timeout=timeout)
        return _run(root, ["jj", "log", "-n", "4"])
    raise ValueError(f"unsupported action: {typ}")


def evaluate(root: Path, fixture: dict[str, Any]) -> dict[str, Any]:
    root = _ensure_external_root(root)
    expected = fixture["expected_files"]
    actual = {
        p: (root / p).read_text(encoding="utf-8") if (root / p).is_file() else None
        for p in expected
    }
    content_ok = all(
        (
            sorted((actual.get(path) or "").splitlines())
            == sorted((expected.get(path) or "").splitlines())
            if path == "tasks/WORKBOARD.md"
            else actual.get(path) == expected.get(path)
        )
        for path in expected
    )
    status = _run(root, ["jj", "status"])
    log = _run(root, ["jj", "log", "-n", "6"])
    # Inspect commit file ownership directly; shared WORKBOARD may occur in both.
    changes = _run(
        root, ["jj", "log", "-r", "all()", "--no-graph", "--template", 'description ++ "\\n"']
    )
    rows = [
        line.strip() for line in changes.splitlines() if line.strip() and "baseline" not in line
    ]
    conventions = (
        len(rows) >= 2
        and any(x.startswith("docs(") for x in rows)
        and any(x.startswith(("feat(", "fix(")) for x in rows)
    )
    clean = "Working copy changes:" not in status
    tracked = {Path(path).as_posix() for path in _run(root, ["jj", "file", "list"]).splitlines()}
    expected_paths = set(expected)
    commit_rows = _run(
        root,
        [
            "jj",
            "log",
            "-r",
            "all()",
            "--no-graph",
            "--template",
            'commit_id ++ "\\t" ++ description ++ "\\n"',
        ],
    )
    task_evidence: dict[str, list[str]] = {"docs": [], "behavior": []}
    for line in commit_rows.splitlines():
        if "\t" not in line:
            continue
        revision, description = line.split("\t", 1)
        family = (
            "docs"
            if description.startswith("docs(")
            else "behavior"
            if description.startswith(("feat(", "fix("))
            else None
        )
        if family:
            changed = _run(
                root, ["jj", "diff", "--from", f"{revision}-", "--to", revision, "--summary"]
            )
            # This is a path-only summary, not patch content or message text.
            changed = changed.replace(os.sep, "/")
            task_path = "tasks/open/docs-guide.md" if family == "docs" else "tasks/open/subtract.md"
            task_slug = "docs-guide" if family == "docs" else "subtract"
            try:
                board = _run(root, ["jj", "file", "show", "tasks/WORKBOARD.md", "-r", revision])
                task_text = _run(root, ["jj", "file", "show", task_path, "-r", revision])
            except RuntimeError:
                board, task_text = "", ""
            files_at_boundary = {
                Path(path).as_posix()
                for path in _run(root, ["jj", "file", "list", "-r", revision]).splitlines()
            }
            if (
                task_path not in files_at_boundary
                or f"- {task_slug}" not in board
                or f"Filed as: {task_slug}" not in task_text
            ):
                changed += "\nTASK_OR_WORKBOARD_BOUNDARY_INVALID"
            task_evidence[family].append(changed)
    docs_task = any(
        "TASK_OR_WORKBOARD_BOUNDARY_INVALID" not in diff
        and "docs/guide.md" in diff
        and "tasks/open/docs-guide.md" in diff
        for diff in task_evidence["docs"]
    )
    fix_task = any(
        "TASK_OR_WORKBOARD_BOUNDARY_INVALID" not in diff
        and "src/math.py" in diff
        and "tasks/open/subtract.md" in diff
        and "tests/test_math.py" in diff
        for diff in task_evidence["behavior"]
    )
    checks = {
        "intended_content_preserved": content_ok,
        "no_unexpected_files": tracked == expected_paths,
        "conventional_descriptions": conventions,
        "documentation_task_in_its_commit": docs_task,
        "behavior_task_and_test_in_its_commit": fix_task,
        "working_copy_clean": clean,
        "commit_history_present": len(rows) >= 2,
    }
    return {
        "pass": all(checks.values()),
        "checks": checks,
        "actual_expected_files": actual,
        "status": status,
        "history": log,
        "descriptions": rows,
    }


def run_episode(
    root: Path,
    fixture: dict[str, Any],
    adapter: Adapter,
    *,
    mode: str,
    max_turns: int = 8,
    max_retries: int = 1,
    action_timeout_s: float = 10,
    state_limit: int | None = 30000,
    observation_limit: int | None = 30000,
    review_script: Callable[[Path, dict[str, Any]], tuple[bool, str]] | None = None,
) -> dict[str, Any]:
    root = _ensure_external_root(root)
    state = copy.deepcopy(INITIAL_STATE)
    history: list[dict[str, str]] = []
    captures = []
    actions = []
    invalid = 0
    outcome = "budget_exhausted"
    budget_reason = "max_turns"
    observation = "Fresh fixture initialized. Inspect repository before changes."
    params = {
        "max_turns": max_turns,
        "max_retries": max_retries,
        "action_timeout_s": action_timeout_s,
        "state_limit": state_limit,
        "observation_limit": observation_limit,
        "role_layout": "user_only",
        "customs_source": "supplied",
        "max_tokens": 1400,
    }
    for turn in range(max_turns):
        if state_limit is not None and len(json.dumps(state)) > state_limit:
            outcome = "budget_exhausted"
            budget_reason = "state_size_limit"
            break
        if observation_limit is not None and len(observation) > observation_limit:
            outcome = "budget_exhausted"
            budget_reason = "observation_size_limit"
            break
        packet = {
            "procedure": PROCEDURE,
            "state_schema": SCHEMA_GUIDANCE,
            "customs": fixture["customs"],
            "state": state,
            "latest_observation": observation,
        }
        if mode == "history_plus_state" and history:
            packet["history"] = history
        msg = [{"role": "user", "content": json.dumps(packet, ensure_ascii=False)}]
        if turn == 0:
            initial_input_hash = hashlib.sha256(
                json.dumps(msg, ensure_ascii=False, sort_keys=True).encode()
            ).hexdigest()
        attempt = 0
        while True:
            started = time.monotonic()
            response = adapter.call(msg, params=params)
            elapsed = (time.monotonic() - started) * 1000
            raw = response.get("content", "")
            entry = {
                "turn": turn,
                "attempt": attempt,
                "messages": msg,
                "request_params": dict(params),
                "response_text": raw,
                "usage": response.get("usage"),
                "duration_ms": response.get("duration_ms", elapsed),
                "response_model": response.get("model"),
                "content_origin": response.get("content_origin", "answer"),
                "state_before": copy.deepcopy(state),
            }
            try:
                proposal = parse_proposal(raw)
                candidate = apply_patch(state, proposal["state_patch"])
            except (ValueError, TypeError) as exc:
                entry["validation_error"] = str(exc)
                entry["state_after"] = copy.deepcopy(state)
                captures.append(entry)
                invalid += 1
                if attempt >= max_retries:
                    outcome = "failure"
                    observation = f"Invalid proposal rejected: {exc}."
                    break
                original = observation
                observation = f"Corrective observation: invalid proposal ({exc}). Original triggering observation: {original}"
                msg[0]["content"] += "\n\n" + json.dumps({"retry_observation": observation})
                attempt += 1
                continue
            state = candidate
            entry["state_patch"] = proposal["state_patch"]
            entry["state_after"] = copy.deepcopy(state)
            entry["action"] = proposal["action"]
            captures.append(entry)
            action = proposal["action"]
            actions.append(action)
            if action["type"] == "finish":
                outcome = "finished"
                observation = "Model proposed finish."
                break
            if action["type"] == "blocked":
                outcome = "blocked"
                observation = "Model reported blocked."
                break
            planned_steps = action["steps"] if action["type"] == "plan" else [action]
            tool_calls: list[dict[str, Any]] = []
            script_reviews: list[dict[str, Any]] = []
            observations: list[str] = []
            for call_index, tool_action in enumerate(planned_steps, start=1):
                action_started = time.monotonic()
                try:
                    result = act(
                        root,
                        tool_action,
                        timeout=action_timeout_s,
                        review_script=review_script,
                        review_records=script_reviews,
                    )
                    tool_error = None
                    observations.append(f"Tool {call_index} ({tool_action['type']}) result:\n{result}")
                except Exception as exc:
                    result = ""
                    tool_error = f"{type(exc).__name__}: {exc}"
                    observations.append(
                        f"Tool {call_index} ({tool_action['type']}) failed: {tool_error}"
                    )
                tool_calls.append(
                    {
                        "action": copy.deepcopy(tool_action),
                        "result": result,
                        "error": tool_error,
                        "duration_ms": (time.monotonic() - action_started) * 1000,
                    }
                )
                if tool_error:
                    break
            observation = "\n\n".join(observations)
            entry["tool_calls"] = tool_calls
            entry["script_reviews"] = script_reviews
            entry["action_error"] = next(
                (call["error"] for call in tool_calls if call["error"]), None
            )
            entry["action_duration_ms"] = sum(call["duration_ms"] for call in tool_calls)
            entry["observation"] = observation
            history.extend(
                [{"role": "assistant", "content": raw}, {"role": "user", "content": observation}]
            )
            break
        if outcome in {"failure", "finished", "blocked"}:
            break
    evaluator = evaluate(root, fixture)
    if outcome == "finished" and not evaluator["pass"]:
        outcome = "failure"
    return {
        "mode": mode,
        "outcome": outcome,
        "state": state,
        "captures": captures,
        "actions": actions,
        "invalid_proposals": invalid,
        "evaluator": evaluator,
        "params": params,
        "adapter": adapter.name,
        "configured_model": adapter.model,
        "returned_models": sorted(
            {
                c["response_model"]
                for c in captures
                if isinstance(c.get("response_model"), str) and c["response_model"]
            }
        ),
        "adapter_config": getattr(
            adapter, "manifest", {"configured_model": adapter.model}
        ),
        "budget_reason": budget_reason if outcome == "budget_exhausted" else None,
        "initial_input_hash": locals().get("initial_input_hash"),
    }


def _script() -> list[str]:
    patch = {
        "progress": ["inspected dirty changes"],
        "next_steps": ["commit docs", "commit behavior", "verify"],
    }
    return [
        json.dumps({"state_patch": patch, "action": {"type": "inspect"}}),
        json.dumps(
            {
                "state_patch": {
                    "progress": ["documentation committed"],
                    "next_steps": ["commit behavior", "verify"],
                },
                "action": {
                    "type": "commit",
                    "paths": ["docs/guide.md", "tasks/open/docs-guide.md", "tasks/WORKBOARD.md"],
                    "description": "docs(guide): clarify supported operation",
                },
            }
        ),
        json.dumps(
            {
                "state_patch": {
                    "progress": ["behavior task is ready for board"],
                    "next_steps": ["commit behavior", "verify"],
                },
                "action": {
                    "type": "write",
                    "path": "tasks/WORKBOARD.md",
                    "content": "- docs-guide\n- subtract\n",
                },
            }
        ),
        json.dumps(
            {
                "state_patch": {
                    "progress": ["behavior change committed"],
                    "next_steps": ["verify clean history"],
                },
                "action": {
                    "type": "commit",
                    "paths": [
                        "src/math.py",
                        "tests/test_math.py",
                        "tasks/open/subtract.md",
                        "tasks/WORKBOARD.md",
                    ],
                    "description": "feat(math): add subtraction operation",
                },
            }
        ),
        json.dumps(
            {
                "state_patch": {"progress": ["repository verified"], "next_steps": []},
                "action": {"type": "inspect"},
            }
        ),
        json.dumps(
            {
                "state_patch": {"progress": ["complete"], "next_steps": []},
                "action": {"type": "finish"},
            }
        ),
    ]


def run_pair(output: Path, *, max_turns: int = 8) -> dict[str, Any]:
    output = _ensure_external_root(output)
    output.mkdir(parents=True, exist_ok=True)
    results = {}
    fingerprints = []
    for mode in ("state_only", "history_plus_state"):
        root = output / mode
        fixture = create_fixture(root)
        fingerprint = hashlib.sha256(
            json.dumps(
                {k: (root / k).read_text() for k in sorted(fixture["expected_files"])},
                sort_keys=True,
            ).encode()
        ).hexdigest()
        fingerprints.append(fingerprint)
        adapter = ScriptedAdapter(_script())
        results[mode] = run_episode(root, fixture, adapter, mode=mode, max_turns=max_turns)
        results[mode]["transport_captures"] = adapter.captured
    paired = {
        "manifest_version": 1,
        "scenario": "dirty repository commit organization",
        "procedure_sha256": hashlib.sha256(PROCEDURE.encode()).hexdigest(),
        "schema_sha256": hashlib.sha256(SCHEMA_GUIDANCE.encode()).hexdigest(),
        "role_layout": "user_only",
        "customs_source": "supplied",
        "repetition": 0,
        "human_interventions": 0,
        "same_initial_snapshot": len(set(fingerprints)) == 1,
        "same_initial_model_input": results["state_only"]["initial_input_hash"]
        == results["history_plus_state"]["initial_input_hash"],
        "fixture_fingerprints": fingerprints,
        "results": results,
        "scripted_demo": True,
        "statistical_claim": False,
    }
    (output / "pair.json").write_text(
        json.dumps(paired, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    summary = {
        m: {
            "outcome": r["outcome"],
            "passed": r["evaluator"]["pass"],
            "calls": len(r["captures"]),
            "actions": len(r["actions"]),
            "tool_calls": sum(len(c.get("tool_calls", [])) for c in r["captures"]),
            "retries": r["invalid_proposals"],
            "latency_ms": sum(c.get("duration_ms", 0) or 0 for c in r["captures"]),
            "request_characters": sum(
                sum(len(m.get("content", "")) for m in c.get("messages", [])) for c in r["captures"]
            ),
            "provider_usage_available": any(c.get("usage") is not None for c in r["captures"]),
        }
        for m, r in results.items()
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return paired


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, help="required output directory outside source checkout"
    )
    parser.add_argument("--max-turns", type=int, default=8)
    args = parser.parse_args(argv)
    if args.output is None:
        parser.error(
            "--output is required; generated runs are never written into source by default"
        )
    result = run_pair(args.output.resolve(), max_turns=args.max_turns)
    print(
        json.dumps(
            {
                m: {"outcome": r["outcome"], "passed": r["evaluator"]["pass"]}
                for m, r in result["results"].items()
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
