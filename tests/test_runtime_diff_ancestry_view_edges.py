from toas.runtime.diff_ancestry_view_edges import build_ancestry_lines, build_diff_lines


def test_build_diff_lines_same_head():
    lineage = [{"id": "n1", "role": "assistant", "content": "hello"}]
    lines = build_diff_lines(
        head_a="n1",
        head_b="n1",
        lineage_a=lineage,
        lineage_b=lineage,
        full=False,
        provenance_marker_fn=lambda _: "[G]",
        content_preview_fn=lambda content, full=False: content,
    )
    assert lines[0].startswith("common ancestor: n1")
    assert "same head" in lines[-1]


def test_build_diff_lines_diverging_and_no_common_raises():
    lineage_a = [{"id": "r", "role": "user", "content": "root"}, {"id": "a", "role": "assistant", "content": "a"}]
    lineage_b = [{"id": "r", "role": "user", "content": "root"}, {"id": "b", "role": "assistant", "content": "b"}]
    lines = build_diff_lines(
        head_a="a",
        head_b="b",
        lineage_a=lineage_a,
        lineage_b=lineage_b,
        full=False,
        provenance_marker_fn=lambda _: "[U]",
        content_preview_fn=lambda content, full=False: content,
    )
    assert any("branch A" in line for line in lines)
    assert any("branch B" in line for line in lines)

    try:
        build_diff_lines(
            head_a="x",
            head_b="y",
            lineage_a=[{"id": "x"}],
            lineage_b=[{"id": "y"}],
            full=False,
            provenance_marker_fn=lambda _: "[?]",
            content_preview_fn=lambda content, full=False: content,
        )
        assert False, "expected SystemExit"
    except SystemExit as exc:
        assert "no common ancestor" in str(exc)


def test_build_diff_lines_handles_no_diverging_branch():
    lineage_a = [{"id": "r", "role": "user", "content": "root"}]
    lineage_b = [{"id": "r", "role": "user", "content": "root"}, {"id": "b", "role": "assistant", "content": "b"}]
    lines = build_diff_lines(
        head_a="r",
        head_b="b",
        lineage_a=lineage_a,
        lineage_b=lineage_b,
        full=False,
        provenance_marker_fn=lambda _: "[U]",
        content_preview_fn=lambda content, full=False: content,
    )
    assert any("(no diverging message)" in line for line in lines)


def test_build_ancestry_lines_applies_depth():
    lineage = [{"id": "n0", "role": "user", "content": "a"}, {"id": "n1", "role": "assistant", "content": "b"}]
    lines = build_ancestry_lines(
        lineage=lineage,
        depth=1,
        full=False,
        provenance_marker_fn=lambda _: "[G]",
        content_preview_fn=lambda content, full=False: content,
    )
    assert lines == ["n1  ASSISTANT  [G]  b"]
