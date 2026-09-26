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
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from ..llm import NO_THINKING, Settings, complete_chat_response

SOURCE_ROOT = Path(__file__).resolve().parents[3]
PROCEDURE = """Organize all supplied dirty changes into coherent commits using the supplied repository customs. Inspect before acting. Preserve all intended content. Every task change must include its task evidence in that commit and keep WORKBOARD references valid at each boundary. Commit documentation and behavior separately. After each successful action, record what it established in progress and replace next_steps with the remaining work. Do not repeat an action when its observation is unchanged unless new evidence justifies it. Report completion only after the working copy is clean and the commit history is correct. Use only these bounded actions: inspect; read with a relative path; write with a relative path and complete text for an existing file; commit with a non-empty list of relative paths and a description; continue; finish; blocked. Do not use arbitrary shell. On every turn return exactly one valid JSON object, with no markdown fence, reasoning, or extra fields. Follow this valid example: {\"state_patch\":{},\"action\":{\"type\":\"inspect\"}}. A patch is a sparse object update. Action examples: {\"type\":\"inspect\"}, {\"type\":\"read\",\"path\":\"README.md\"}, {\"type\":\"write\",\"path\":\"README.md\",\"content\":\"complete file text\"}, {\"type\":\"commit\",\"paths\":[\"README.md\"],\"description\":\"docs(readme): update usage\"}, or {\"type\":\"continue\"}/{\"type\":\"finish\"}/{\"type\":\"blocked\"}. Inspect and read the actual dirty files before deciding partitions. A commit selects only its listed paths; remaining changes stay available for later actions."""
SCHEMA_GUIDANCE = "State fields: goal (objective string); progress (concrete completed actions and findings that may matter later); next_steps (only remaining actionable work); artifacts (produced paths); blockers (obstacles preventing progress); notes (object with constraints, accepted_decisions, pending_proposals, uncertainties arrays). After a successful action, update progress and remove completed work from next_steps. This generic state shape is authored for this experiment, not supplied by the paper."
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
CUSTOMS = "Use conventional lowercase commit descriptions (`docs(scope): summary` or `fix(scope): summary`). Each task change includes its task file in the same commit; update WORKBOARD references accordingly."


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
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"response is not JSON: {exc.msg}") from exc
    if not isinstance(obj, dict) or set(obj) != {"state_patch", "action"}:
        raise ValueError("response must contain exactly state_patch and action")
    if not isinstance(obj["action"], dict) or obj["action"].get("type") not in {
        "inspect",
        "read",
        "write",
        "commit",
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
    root.mkdir(parents=True, exist_ok=True)
    (root / "AGENTS.md").write_text(
        "Use conventional commits. Keep each task's task file in its commit.\n", encoding="utf-8"
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
                "prefix": "fix(",
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


def act(root: Path, action: dict[str, Any], *, timeout: float) -> str:
    root = _ensure_external_root(root)
    typ = action["type"]
    if typ in {"continue", "finish", "blocked"}:
        return ""
    if typ == "inspect":
        return (
            _run(root, ["jj", "status"])
            + "\n"
            + _run(root, ["jj", "diff", "--summary"])
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
        rel, content = action.get("path"), action.get("content")
        if not isinstance(rel, str) or not isinstance(content, str):
            raise ValueError("write requires path and text content")
        p = safe_path(root, rel)
        if p.is_symlink() or not p.is_file():
            raise ValueError("write target must be an existing regular fixture file")
        p.write_text(content, encoding="utf-8")
        return f"Updated {rel} ({len(content)} characters)."
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
    content_ok = actual == expected
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
        and any(x.startswith("fix(") for x in rows)
    )
    clean = "Working copy changes:" not in status
    tracked = set(_run(root, ["jj", "file", "list"]).splitlines())
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
    task_evidence: dict[str, list[str]] = {"docs": [], "fix": []}
    for line in commit_rows.splitlines():
        if "\t" not in line:
            continue
        revision, description = line.split("\t", 1)
        family = (
            "docs"
            if description.startswith("docs(")
            else "fix"
            if description.startswith("fix(")
            else None
        )
        if family:
            changed = _run(
                root, ["jj", "diff", "--from", f"{revision}-", "--to", revision, "--summary"]
            )
            task_path = "tasks/open/docs-guide.md" if family == "docs" else "tasks/open/subtract.md"
            task_slug = "docs-guide" if family == "docs" else "subtract"
            try:
                board = _run(root, ["jj", "file", "show", "tasks/WORKBOARD.md", "-r", revision])
                task_text = _run(root, ["jj", "file", "show", task_path, "-r", revision])
            except RuntimeError:
                board, task_text = "", ""
            files_at_boundary = set(_run(root, ["jj", "file", "list", "-r", revision]).splitlines())
            if (
                task_path not in files_at_boundary
                or f"- {task_slug}" not in board
                or f"Filed as: {task_slug}" not in task_text
            ):
                changed += "\nTASK_OR_WORKBOARD_BOUNDARY_INVALID"
            task_evidence[family].append(changed)
    docs_task = any(
        "docs/guide.md" in diff and "tasks/open/docs-guide.md" in diff
        for diff in task_evidence["docs"]
    )
    fix_task = any(
        "src/math.py" in diff and "tasks/open/subtract.md" in diff and "tests/test_math.py" in diff
        for diff in task_evidence["fix"]
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
        "max_tokens": 900,
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
            action_started = time.monotonic()
            try:
                observation = act(root, action, timeout=action_timeout_s)
                entry["action_error"] = None
            except Exception as exc:
                observation = f"Action failed: {type(exc).__name__}: {exc}"
                entry["action_error"] = observation
            entry["action_duration_ms"] = (time.monotonic() - action_started) * 1000
            entry["observation"] = observation
            history.extend(
                [{"role": "assistant", "content": raw}, {"role": "user", "content": observation}]
            )
            break
        if outcome in {"failure", "finished", "blocked"}:
            break
    evaluator = evaluate(root, fixture)
    if outcome == "finished" and not evaluator["checks"]["working_copy_clean"]:
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
        "model": adapter.model,
        "adapter_config": getattr(adapter, "manifest", {"model": adapter.model}),
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
                    "description": "fix(math): add subtraction operation",
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
