from __future__ import annotations

from collections.abc import Callable


def run_heads(
    *,
    ensure_file: Callable,
    resolve_events_path: Callable,
    operator_heads_lines: Callable,
    source_tokens: list[str] | None = None,
    print_fn: Callable = print,
) -> None:
    events_path = resolve_events_path()
    ensure_file(events_path)
    for line in operator_heads_lines(events_path=events_path, source_tokens=source_tokens).lines:
        print_fn(line)


def run_intents(
    *,
    ensure_file: Callable,
    resolve_events_path: Callable,
    operator_intents_lines: Callable,
    print_fn: Callable = print,
) -> None:
    events_path = resolve_events_path()
    ensure_file(events_path)
    for line in operator_intents_lines(events_path=events_path).lines:
        print_fn(line)


def run_transcript(
    *,
    ensure_file: Callable,
    resolve_events_path: Callable,
    operator_transcript_text: Callable,
    head_id: str | None = None,
    print_fn: Callable = print,
) -> None:
    events_path = resolve_events_path()
    ensure_file(events_path)
    out = operator_transcript_text(events_path=events_path, head_id=head_id)
    print_fn(out.text, end="")


def run_llm_input(
    *,
    ensure_file: Callable,
    resolve_events_path: Callable,
    operator_llm_input_messages: Callable,
    print_blocks_with_newline: Callable,
    head_id: str | None = None,
    envelope: bool = False,
) -> None:
    events_path = resolve_events_path()
    ensure_file(events_path)
    out = operator_llm_input_messages(events_path=events_path, head_id=head_id, envelope=envelope)
    print_blocks_with_newline(out.messages, "\n")


def run_prompt(
    *,
    ensure_file: Callable,
    resolve_events_path: Callable,
    operator_prompt_text: Callable,
    ref: str,
    mode: str = "direct",
    constraints: list[str] | None = None,
    print_fn: Callable = print,
) -> None:
    events_path = resolve_events_path()
    ensure_file(events_path)
    out = operator_prompt_text(events_path=events_path, ref=ref, mode=mode, constraints=constraints)
    print_fn(out.text)


def run_prompts(
    *,
    operator_prompt_list_lines: Callable,
    prefix: str | None = None,
    print_fn: Callable = print,
) -> None:
    for line in operator_prompt_list_lines(prefix=prefix).lines:
        print_fn(line)
