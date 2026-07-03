from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from toas import cli_surface_commands as surface


@dataclass
class _Lines:
    lines: list[str]


@dataclass
class _Text:
    text: str


@dataclass
class _Messages:
    messages: list[dict]


def test_run_heads_ensures_events_and_prints_lines():
    calls = []
    events_path = Path("events.jsonl")

    surface.run_heads(
        ensure_file=lambda path: calls.append(("ensure", path)),
        resolve_events_path=lambda: events_path,
        operator_heads_lines=lambda *, events_path, source_tokens=None: calls.append(("heads", events_path, source_tokens)) or _Lines(["n2", "n1"]),
        source_tokens=["segments", "hot"],
        print_fn=lambda line: calls.append(("print", line)),
    )

    assert calls == [
        ("ensure", events_path),
        ("heads", events_path, ["segments", "hot"]),
        ("print", "n2"),
        ("print", "n1"),
    ]


def test_run_intents_ensures_events_and_prints_lines():
    calls = []
    events_path = Path("events.jsonl")

    surface.run_intents(
        ensure_file=lambda path: calls.append(("ensure", path)),
        resolve_events_path=lambda: events_path,
        operator_intents_lines=lambda *, events_path: calls.append(("intents", events_path)) or _Lines(["intent"]),
        print_fn=lambda line: calls.append(("print", line)),
    )

    assert calls == [("ensure", events_path), ("intents", events_path), ("print", "intent")]


def test_run_transcript_passes_head_and_preserves_text_end():
    calls = []
    events_path = Path("events.jsonl")

    surface.run_transcript(
        ensure_file=lambda path: calls.append(("ensure", path)),
        resolve_events_path=lambda: events_path,
        operator_transcript_text=lambda *, events_path, head_id: calls.append(("transcript", events_path, head_id))
        or _Text("body\n"),
        head_id="n4",
        print_fn=lambda text, end="\n": calls.append(("print", text, end)),
    )

    assert calls == [
        ("ensure", events_path),
        ("transcript", events_path, "n4"),
        ("print", "body\n", ""),
    ]


def test_run_llm_input_renders_messages_with_lf():
    calls = []
    events_path = Path("events.jsonl")
    messages = [{"role": "user", "content": "hello"}]

    surface.run_llm_input(
        ensure_file=lambda path: calls.append(("ensure", path)),
        resolve_events_path=lambda: events_path,
        operator_llm_input_messages=lambda *, events_path, head_id, envelope: calls.append(
            ("llm", events_path, head_id, envelope)
        )
        or _Messages(messages),
        print_blocks_with_newline=lambda nodes, newline: calls.append(("render", nodes, newline)),
        head_id="n5",
        envelope=True,
    )

    assert calls == [
        ("ensure", events_path),
        ("llm", events_path, "n5", True),
        ("render", messages, "\n"),
    ]


def test_run_prompt_passes_selector_options():
    calls = []
    events_path = Path("events.jsonl")

    surface.run_prompt(
        ensure_file=lambda path: calls.append(("ensure", path)),
        resolve_events_path=lambda: events_path,
        operator_prompt_text=lambda *, events_path, ref, mode, constraints: calls.append(
            ("prompt", events_path, ref, mode, constraints)
        )
        or _Text("prompt body"),
        ref="core/default",
        mode="full",
        constraints=["repo"],
        print_fn=lambda text: calls.append(("print", text)),
    )

    assert calls == [
        ("ensure", events_path),
        ("prompt", events_path, "core/default", "full", ["repo"]),
        ("print", "prompt body"),
    ]


def test_run_prompts_prints_prefix_filtered_lines():
    calls = []

    surface.run_prompts(
        operator_prompt_list_lines=lambda *, prefix: calls.append(("prompts", prefix)) or _Lines(["a", "b"]),
        prefix="core",
        print_fn=lambda line: calls.append(("print", line)),
    )

    assert calls == [("prompts", "core"), ("print", "a"), ("print", "b")]
