
from toas.runtime.session_file_edges import (
    read_text_preserve_newlines,
    write_text_with_newline_style,
)


def test_read_text_preserve_newlines(tmp_path):
    path = tmp_path / "session.md"
    path.write_text("a\r\nb\r\n", encoding="utf-8", newline="")
    assert read_text_preserve_newlines(path) == "a\r\nb\r\n"


def test_write_text_with_newline_style_uses_adapter(tmp_path):
    path = tmp_path / "session.md"
    write_text_with_newline_style(
        path=path,
        text="a\nb\n",
        newline="\r\n",
        apply_newline_style_fn=lambda text, newline: text.replace("\n", newline),
    )
    with path.open("r", encoding="utf-8", newline="") as handle:
        assert handle.read() == "a\r\nb\r\n"
