from __future__ import annotations

import contextlib
import io
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class ReplayScriptDeps:
    ensure_file: Callable[[Path], None]
    session_path: Path
    events_path: Path
    load_replay_steps: Callable[[Path], list]
    render_prompt_append: Callable[..., str]
    render_procedure_append: Callable[[str], str]
    append_text_block: Callable[..., int]
    read_log: Callable[[str], list[dict]]
    run_step_local: Callable[[], None]
    read_text_preserve_newlines: Callable[[Path], str]
    load_prompt_ref: Callable[[str], str]
    write_replay_artifact: Callable[..., None]
    print_fn: Callable[[str], None]


def run_replay_script_local(
    script_path: str,
    *,
    output_path: str | None = None,
    dry_run: bool = False,
    deps: ReplayScriptDeps,
) -> None:
    deps.ensure_file(deps.session_path)
    deps.ensure_file(deps.events_path)
    script = Path(script_path)
    replay_steps = deps.load_replay_steps(script)
    event_rows: list[dict] = []
    for index, replay_step in enumerate(replay_steps, start=1):
        append_content = replay_step.append
        source = replay_step.source
        if source == "prompt":
            append_content = deps.render_prompt_append(
                append_content.strip(),
                load_prompt_ref=deps.load_prompt_ref,
            )
        elif source == "procedure":
            append_content = deps.render_procedure_append(append_content.strip())

        appended_chars = deps.append_text_block(session_path=deps.session_path, text=append_content)
        row = {
            "index": index,
            "source": source,
            "run_step": replay_step.run_step,
            "appended_chars": appended_chars,
        }
        if replay_step.run_step and not dry_run:
            before = len(deps.read_log(str(deps.events_path)))
            captured = io.StringIO()
            with contextlib.redirect_stdout(captured):
                deps.run_step_local()
            after = len(deps.read_log(str(deps.events_path)))
            row["stdout"] = captured.getvalue().rstrip("\n")
            row["event_delta"] = after - before
        event_rows.append(row)

    events_tail = deps.read_log(str(deps.events_path))[-20:]
    session_tail = deps.read_text_preserve_newlines(deps.session_path)[-4000:]
    if output_path:
        artifact_path = Path(output_path)
    else:
        artifact_path = Path(".toas/replays") / f"{script.stem}.json"
    deps.write_replay_artifact(
        artifact_path=artifact_path,
        script_path=script,
        dry_run=dry_run,
        steps=event_rows,
        events_tail=events_tail,
        session_tail=session_tail,
    )
    deps.print_fn(f"replay-script: wrote artifact {artifact_path}")

