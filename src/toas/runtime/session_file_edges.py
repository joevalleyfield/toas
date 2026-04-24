from pathlib import Path


def read_text_preserve_newlines(path: Path) -> str:
    with path.open("r", encoding="utf-8", newline="", errors="replace") as handle:
        return handle.read()


def write_text_with_newline_style(
    *,
    path: Path,
    text: str,
    newline: str,
    apply_newline_style_fn,
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(apply_newline_style_fn(text, newline))
