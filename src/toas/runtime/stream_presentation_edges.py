from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..llm import PromptProgress
else:
    PromptProgress = Any


THINKING_OPEN_MARKER = "## TOAS:THINKING\n"
THINKING_CLOSE_MARKER = "\n## /TOAS:THINKING\n"


def render_prompt_progress_line(progress: PromptProgress) -> str:
    pct = int((progress.processed * 100) / progress.total) if progress.total > 0 else 0
    bits = [f"prompt {progress.processed}/{progress.total} ({pct}%)"]
    if progress.cache is not None:
        bits.append(f"cache={progress.cache}")
    if progress.time_ms is not None:
        bits.append(f"t={progress.time_ms}ms")
    return " | ".join(bits)


def render_prompt_progress_diag_line(
    *,
    callbacks: int,
    rendered: int,
    allow_updates: bool,
    last_text: str,
) -> str:
    return (
        "[diag] prompt_progress: "
        f"callbacks={callbacks}, "
        f"rendered={rendered}, "
        f"allow_updates={allow_updates}, "
        f"last_text={last_text!r}"
    )
