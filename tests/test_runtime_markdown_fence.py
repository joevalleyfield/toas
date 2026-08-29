from __future__ import annotations

from toas.runtime.markdown_fence import scan_markdown_fences


def test_scan_markdown_fences_reports_info_body_and_source_locations():
    content = "before\n```bash exec\necho hi\n```\nafter\n"

    fences = scan_markdown_fences(content)

    assert len(fences) == 1
    fence = fences[0]
    assert fence.info_string == "bash exec"
    assert fence.info_tokens == ("bash", "exec")
    assert fence.body == "echo hi\n"
    assert fence.opening_line == 2
    assert fence.closing_line == 4
    assert content[fence.opening_offset : fence.closing_offset].startswith("```bash exec")
    assert fence.fence_length == 3


def test_scan_markdown_fences_keeps_shorter_inner_fence_text_in_outer_body():
    content = "````text\n```yaml\nexample\n```\n````\n"

    fences = scan_markdown_fences(content)

    assert len(fences) == 1
    assert fences[0].body == "```yaml\nexample\n```\n"


def test_scan_markdown_fences_ignores_unterminated_opening():
    assert scan_markdown_fences("```bash exec\necho hi\n") == []


def test_scan_markdown_fences_requires_matching_or_longer_closing_fence():
    content = "````bash exec\necho ``` safely\n```\n````\n"

    fences = scan_markdown_fences(content)

    assert len(fences) == 1
    assert fences[0].fence_length == 4
    assert fences[0].body == "echo ``` safely\n```\n"
