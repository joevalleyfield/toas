from __future__ import annotations

from .llm import PromptProgress
from .runtime.stream_presentation_edges import (
    THINKING_CLOSE_MARKER as THINKING_CLOSE_RUNTIME_MARKER,
)
from .runtime.stream_presentation_edges import (
    THINKING_OPEN_MARKER as THINKING_OPEN_RUNTIME_MARKER,
)
from .runtime.stream_presentation_edges import (
    render_prompt_progress_diag_line as render_runtime_prompt_progress_diag_line,
)
from .runtime.stream_presentation_edges import (
    render_prompt_progress_line as render_runtime_prompt_progress_line,
)


class ClosedSetMarkerStreamEscaper:
    _MARKERS = ("## TOAS:SYSTEM", "## TOAS:USER", "## TOAS:ASSISTANT")

    def __init__(self) -> None:
        self._line_start = True
        self._probe = ""

    def observe_literal_text(self, text: str) -> None:
        for ch in text:
            self._line_start = ch == "\n"
        self._probe = ""

    def feed(self, text: str) -> str:
        out: list[str] = []
        for ch in text:
            if self._line_start:
                self._probe += ch
                if any(marker.startswith(self._probe) for marker in self._MARKERS):
                    continue
                if ch == "\n":
                    line = self._probe[:-1]
                    if line in self._MARKERS:
                        out.append("\\" + line + "\n")
                    else:
                        out.append(self._probe)
                    self._probe = ""
                    self._line_start = True
                    continue
                out.append(self._probe)
                self._probe = ""
                self._line_start = False
                continue
            out.append(ch)
            if ch == "\n":
                self._line_start = True
        if self._probe and not any(marker.startswith(self._probe) for marker in self._MARKERS):
            out.append(self._probe)
            self._probe = ""
            self._line_start = False
        return "".join(out)

    def flush(self) -> str:
        if not self._probe:
            return ""
        if self._probe in self._MARKERS:
            text = "\\" + self._probe
        else:
            text = self._probe
        self._probe = ""
        self._line_start = text.endswith("\n")
        return text


class StreamPresenter:
    def __init__(
        self,
        *,
        stream_state: dict[str, object],
        stream_thinking: bool,
        stream_prompt_progress: bool,
    ) -> None:
        self.stream_state = stream_state
        self.stream_thinking = stream_thinking
        self.stream_prompt_progress = stream_prompt_progress
        self.thinking_open = False
        self.progress_shown = False
        self.progress_last_text = ""
        self.progress_allow_updates = True
        self.progress_callbacks = 0
        self.progress_rendered = 0
        self._escaper = ClosedSetMarkerStreamEscaper()

    def on_prompt_progress(self, progress: PromptProgress) -> None:
        if not self.stream_prompt_progress:
            return
        self.progress_callbacks += 1
        if not self.progress_allow_updates:
            return
        text = render_runtime_prompt_progress_line(progress)
        if text == self.progress_last_text:
            return
        print(f"\r{text}", end="", flush=True)
        self.progress_shown = True
        self.progress_last_text = text
        self.progress_rendered += 1
        self.stream_state["emitted"] = True
        self.stream_state["ends_with_newline"] = False

    def on_delta(self, delta: str) -> None:
        if not delta:
            return
        self.progress_allow_updates = False
        if self.progress_shown:
            print("", flush=True)
            self.progress_shown = False
            self._escaper.observe_literal_text("\n")
        if self.thinking_open:
            pending = self._escaper.flush()
            if pending:
                print(pending, end="", flush=True)
            print(THINKING_CLOSE_RUNTIME_MARKER, end="", flush=True)
            self.thinking_open = False
            self._escaper.observe_literal_text(THINKING_CLOSE_RUNTIME_MARKER)
        escaped = self._escaper.feed(delta)
        if escaped:
            print(escaped, end="", flush=True)
        self.stream_state["emitted"] = True
        self.stream_state["ends_with_newline"] = delta.endswith("\n")

    def on_reasoning_delta(self, delta: str) -> None:
        if not self.stream_thinking or not delta:
            return
        self.progress_allow_updates = False
        if self.progress_shown:
            print("", flush=True)
            self.progress_shown = False
            self._escaper.observe_literal_text("\n")
        if not self.thinking_open:
            pending = self._escaper.flush()
            if pending:
                print(pending, end="", flush=True)
            print(THINKING_OPEN_RUNTIME_MARKER, end="", flush=True)
            self.thinking_open = True
            self._escaper.observe_literal_text(THINKING_OPEN_RUNTIME_MARKER)
        escaped = self._escaper.feed(delta)
        if escaped:
            print(escaped, end="", flush=True)
        self.stream_state["emitted"] = True
        self.stream_state["ends_with_newline"] = delta.endswith("\n")

    def finalize(self) -> None:
        pending = self._escaper.flush()
        if pending:
            print(pending, end="", flush=True)
            self.stream_state["emitted"] = True
            self.stream_state["ends_with_newline"] = pending.endswith("\n")
        if self.thinking_open:
            print(THINKING_CLOSE_RUNTIME_MARKER, end="", flush=True)
            self.stream_state["emitted"] = True
            self.stream_state["ends_with_newline"] = True
            self._escaper.observe_literal_text(THINKING_CLOSE_RUNTIME_MARKER)
        if self.progress_shown:
            print("", flush=True)
            self.stream_state["ends_with_newline"] = True
            self._escaper.observe_literal_text("\n")

    def prompt_progress_diag_line(self) -> str:
        return render_runtime_prompt_progress_diag_line(
            callbacks=self.progress_callbacks,
            rendered=self.progress_rendered,
            allow_updates=self.progress_allow_updates,
            last_text=self.progress_last_text,
        )
