from toas.runtime.lineage_edges import (
    find_common_ancestor,
    first_after,
    format_ancestry_line,
    format_branch_header,
    format_common_ancestor_line,
    format_diverging_line,
    format_no_diverging_line,
)


def test_find_common_ancestor_returns_latest_shared_event():
    lineage_a = [{"id": "r"}, {"id": "a1"}, {"id": "a2"}]
    lineage_b = [{"id": "r"}, {"id": "a1"}, {"id": "b1"}]
    assert find_common_ancestor(lineage_a, lineage_b) == {"id": "a1"}


def test_find_common_ancestor_returns_none_when_disjoint():
    assert find_common_ancestor([{"id": "x"}], [{"id": "y"}]) is None


def test_first_after_returns_next_or_none():
    lineage = [{"id": "r"}, {"id": "a"}, {"id": "b"}]
    assert first_after(lineage, "a") == {"id": "b"}
    assert first_after(lineage, "b") is None
    assert first_after(lineage, "missing") is None


def test_lineage_formatters_render_expected_rows():
    assert format_common_ancestor_line(ancestor_id="root", marker="[U]", preview="hello") == 'common ancestor: root  [U]  "hello"'
    assert format_branch_header(label="A", head_id="n1") == "branch A (head n1):"
    assert format_no_diverging_line() == "  (no diverging message)"
    assert format_diverging_line(event_id="n2", role="assistant", marker="[G]", preview="x") == '  n2  ASSISTANT  [G]  "x"'
    assert format_ancestry_line(event_id="n3", role="user", marker="[U]", display="msg") == "n3  USER  [U]  msg"
