from pathlib import Path
from types import SimpleNamespace

from toas.cli_replay_script import ReplayScriptDeps, run_replay_script


def test_run_replay_script_dry_run_writes_artifact_and_skips_step(tmp_path):
    session_path = tmp_path / "session.md"
    events_path = tmp_path / "events.jsonl"
    calls: list[str] = []
    artifact_payload: dict = {}
    replay_steps = [
        SimpleNamespace(append="protocol/terse_v1", source="prompt", run_step=False),
        SimpleNamespace(append="repo_discovery_triage_v1", source="procedure", run_step=False),
    ]

    def ensure_file(path: Path) -> None:
        path.touch(exist_ok=True)

    def append_text_block(*, session_path: Path, text: str) -> int:
        existing = session_path.read_text(encoding="utf-8") if session_path.exists() else ""
        session_path.write_text(existing + text, encoding="utf-8")
        return len(text)

    def write_replay_artifact(**kwargs):
        artifact_payload.update(kwargs)

    def print_fn(message: str):
        calls.append(message)

    deps = ReplayScriptDeps(
        ensure_file=ensure_file,
        session_path=session_path,
        events_path=events_path,
        load_replay_steps=lambda _script: replay_steps,
        render_prompt_append=lambda ref, *, load_prompt_ref: f"## TOAS:SYSTEM\n\n{load_prompt_ref(ref)}\n",
        render_procedure_append=lambda name: f"## TOAS:USER\n\n{name}\n",
        append_text_block=append_text_block,
        read_log=lambda _path: [],
        run_step=lambda: calls.append("step"),
        read_text_preserve_newlines=lambda path: path.read_text(encoding="utf-8"),
        load_prompt_ref=lambda ref: f"PROMPT<{ref}>",
        write_replay_artifact=write_replay_artifact,
        print_fn=print_fn,
    )

    run_replay_script("scenario.yaml", dry_run=True, deps=deps)

    assert "step" not in calls
    assert calls[-1] == "replay-script: wrote artifact .toas/replays/scenario.json"
    assert artifact_payload["dry_run"] is True
    assert len(artifact_payload["steps"]) == 2


def test_run_replay_script_runs_step_and_records_stdout_and_delta(tmp_path):
    session_path = tmp_path / "session.md"
    events_path = tmp_path / "events.jsonl"
    artifact_payload: dict = {}
    messages: list[str] = []
    replay_steps = [SimpleNamespace(append="hello", source="user", run_step=True)]
    events = [{"id": "n0"}]

    def ensure_file(path: Path) -> None:
        path.touch(exist_ok=True)

    def append_text_block(*, session_path: Path, text: str) -> int:
        session_path.write_text(text, encoding="utf-8")
        return len(text)

    def run_step() -> None:
        print("## TOAS:ASSISTANT\n\nhi\n")
        events.append({"id": "n1"})

    def write_replay_artifact(**kwargs):
        artifact_payload.update(kwargs)

    deps = ReplayScriptDeps(
        ensure_file=ensure_file,
        session_path=session_path,
        events_path=events_path,
        load_replay_steps=lambda _script: replay_steps,
        render_prompt_append=lambda ref, *, load_prompt_ref: ref,
        render_procedure_append=lambda name: name,
        append_text_block=append_text_block,
        read_log=lambda _path: list(events),
        run_step=run_step,
        read_text_preserve_newlines=lambda path: path.read_text(encoding="utf-8"),
        load_prompt_ref=lambda ref: ref,
        write_replay_artifact=write_replay_artifact,
        print_fn=lambda m: messages.append(m),
    )

    run_replay_script("scenario.yaml", output_path="out.json", dry_run=False, deps=deps)

    step_row = artifact_payload["steps"][0]
    assert step_row["stdout"] == "## TOAS:ASSISTANT\n\nhi"
    assert step_row["event_delta"] == 1
    assert artifact_payload["artifact_path"] == Path("out.json")
    assert messages[-1] == "replay-script: wrote artifact out.json"
