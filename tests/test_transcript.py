import pytest

from toas.transcript import parse_transcript, render_transcript


def test_parse_transcript_reads_ordered_blocks():
    transcript = """\
## TOAS:USER
hello

## TOAS:ASSISTANT
hi
"""

    assert parse_transcript(transcript) == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
    ]


def test_parse_transcript_accepts_control_blocks():
    transcript = """\
## TOAS:CONTROL
/help tools

## TOAS:USER
hello
"""
    assert parse_transcript(transcript) == [
        {"role": "control", "content": "/help tools"},
        {"role": "user", "content": "hello"},
    ]


def test_parse_transcript_preserves_internal_newlines():
    transcript = """\
## TOAS:USER
line one
line two

still user
"""

    assert parse_transcript(transcript) == [
        {"role": "user", "content": "line one\nline two\n\nstill user"},
    ]


def test_parse_transcript_ignores_text_before_first_header():
    transcript = """\
leading text
that is not a block

## TOAS:USER
hello
"""

    assert parse_transcript(transcript) == [
        {"role": "user", "content": "hello"},
    ]


def test_parse_transcript_treats_non_toas_markers_as_content():
    transcript = """\
## TOAS:USER
hello

## 

## TOAS:ASSISTANT
hi
"""

    assert parse_transcript(transcript) == [
        {"role": "user", "content": "hello\n\n##"},
        {"role": "assistant", "content": "hi"},
    ]


def test_parse_transcript_errors_on_invalid_toas_marker():
    transcript = """\
## TOAS:USER
hello
## TOAS:BOT
nope
"""

    with pytest.raises(ValueError, match="invalid transcript marker at line 3"):
        parse_transcript(transcript)


def test_parse_transcript_allows_marker_like_content_inside_code_fences():
    transcript = """\
## TOAS:USER
Here is an example:
```markdown
## TOAS:<ROLE> [[handle]]
## TOAS:BOT
```
Done.
"""
    parsed = parse_transcript(transcript)
    assert len(parsed) == 1
    assert parsed[0]["role"] == "user"
    assert "## TOAS:<ROLE> [[handle]]" in parsed[0]["content"]
    assert "## TOAS:BOT" in parsed[0]["content"]


def test_parse_transcript_preserves_role_markers_inside_code_fences_without_splitting():
    transcript = """\
## TOAS:USER
Here is code:
```python
# A comment
## TOAS:USER
print("hello")
## TOAS:ASSISTANT
```
Still in user turn.
"""
    parsed = parse_transcript(transcript)
    assert len(parsed) == 1
    assert parsed[0]["role"] == "user"
    assert 'print("hello")' in parsed[0]["content"]
    assert "Still in user turn." in parsed[0]["content"]


def test_parse_transcript_handles_nested_code_fences():
    transcript = """\
## TOAS:USER
Outer:
`````text
```markdown
## TOAS:<ROLE>
```
`````
After outer fence.
## TOAS:ASSISTANT
Response.
"""
    parsed = parse_transcript(transcript)
    assert len(parsed) == 2
    assert parsed[0]["role"] == "user"
    assert "## TOAS:<ROLE>" in parsed[0]["content"]
    assert "After outer fence." in parsed[0]["content"]
    assert parsed[1]["role"] == "assistant"
    assert parsed[1]["content"] == "Response."


def test_parse_transcript_preserves_frontier_after_indented_fences_in_yaml_plan():
    plan = (
        "```yaml\n"
        "- tool_name: write_file\n"
        "  args:\n"
        "    path: example.md\n"
        "    content: |\n"
        "      ```text\n"
        "      Example.\n"
        "      ```\n"
        "```"
    )
    transcript = f"## TOAS:ASSISTANT\n{plan}\n## TOAS:USER\n## RESULT\nDone.\n## TOAS:USER\n$ jj st\n"

    assert parse_transcript(transcript) == [
        {"role": "assistant", "content": plan},
        {"role": "user", "content": "## RESULT\nDone."},
        {"role": "user", "content": "$ jj st"},
    ]


@pytest.mark.parametrize("indent", ["    ", "\t", " \t"])
def test_parse_transcript_does_not_open_fence_at_four_columns(indent):
    transcript = f"## TOAS:ASSISTANT\nAn example:\n{indent}~~~text\n## TOAS:USER\nnext\n"

    assert parse_transcript(transcript) == [
        {"role": "assistant", "content": f"An example:\n{indent}~~~text"},
        {"role": "user", "content": "next"},
    ]


@pytest.mark.parametrize("fence", ["```", "~~~"])
def test_parse_transcript_honors_three_space_fences(fence):
    body = f"   {fence}text\n## TOAS:USER\nExample.\n   {fence}\t"
    transcript = f"## TOAS:ASSISTANT\n{body}\n## TOAS:USER\nnext\n"

    assert parse_transcript(transcript) == [
        {"role": "assistant", "content": body.strip()},
        {"role": "user", "content": "next"},
    ]


def test_parse_transcript_keeps_unclosed_fence_literal_at_eof():
    body = "Example:\n```text\n## TOAS:USER\n$ jj st"
    transcript = f"## TOAS:ASSISTANT\n{body}\n"

    assert parse_transcript(transcript) == [{"role": "assistant", "content": body}]


def test_parse_transcript_handles_dogfood_read_file_result_with_grammar_specimen():
    transcript = """\
## TOAS:USER
## RESULT [tool OK read_file]
`````text toas-output kind=file
# Notes
```markdown
## TOAS:<ROLE> [[handle]]
```
`````
## TOAS:USER
next turn
"""
    parsed = parse_transcript(transcript)
    assert len(parsed) == 2
    assert parsed[0]["role"] == "user"
    assert "## TOAS:<ROLE> [[handle]]" in parsed[0]["content"]
    assert parsed[1]["role"] == "user"
    assert parsed[1]["content"] == "next turn"



def test_parse_transcript_enforces_system_once_at_top():
    transcript = """\
## TOAS:USER
hello

## TOAS:SYSTEM
nope
"""

    with pytest.raises(ValueError, match="SYSTEM block must appear only once at the top"):
        parse_transcript(transcript)


def test_render_transcript_escapes_line_start_markers_in_content():
    rendered = render_transcript(
        [
            {"role": "user", "content": "line one\n## TOAS:ASSISTANT\nline two"},
        ]
    )

    assert rendered == "## TOAS:USER\nline one\n\\## TOAS:ASSISTANT\nline two\n"


def test_render_transcript_escapes_only_closed_set_role_markers():
    rendered = render_transcript(
        [
            {
                "role": "user",
                "content": "## TOAS:USER\n## TOAS:ASSISTANT\n## TOAS:SYSTEM\n## TOAS:CONTROL\n## TOAS:THINKING\n## RESULT",
            },
        ]
    )

    assert "\\## TOAS:USER" in rendered
    assert "\\## TOAS:ASSISTANT" in rendered
    assert "\\## TOAS:SYSTEM" in rendered
    assert "\\## TOAS:CONTROL" in rendered
    assert "## TOAS:THINKING" in rendered
    assert "\\## TOAS:THINKING" not in rendered
    assert "## RESULT" in rendered


def test_parse_transcript_round_trip_unescapes_closed_set_role_markers():
    original = [
        {
            "role": "assistant",
            "content": "doc\n## TOAS:USER\n## TOAS:ASSISTANT\n## TOAS:SYSTEM\nend",
        }
    ]
    rendered = render_transcript(original)
    parsed = parse_transcript(rendered)
    assert parsed == original


def test_parse_transcript_ignores_toas_thinking_projection_blocks():
    transcript = """\
## TOAS:USER
hello

## TOAS:THINKING
internal token trace
more trace
## /TOAS:THINKING

## TOAS:ASSISTANT
hi
"""

    assert parse_transcript(transcript) == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
    ]


def test_render_transcript_rejects_invalid_role_marker():
    with pytest.raises(ValueError, match="invalid transcript role"):
        render_transcript([{"role": "tool", "content": "nope"}])


def test_normalize_bind_index_out_of_range():
    from toas.transcript import _normalize_bind_index

    with pytest.raises(ValueError, match="bind index out of range"):
        _normalize_bind_index(-1, [{"role": "user"}])

    with pytest.raises(ValueError, match="bind index out of range"):
        _normalize_bind_index(5, [{"role": "user"}])  # len(log)==1, 5 > 1

    # Valid in-range value returns it unchanged
    assert _normalize_bind_index(1, [{"role": "user"}]) == 1


def test_normalize_anchor_index_out_of_range():
    from toas.transcript import _normalize_anchor_index

    nodes = [{"role": "user"}]
    log = [{"role": "user"}]
    with pytest.raises(ValueError, match="anchor index out of range"):
        _normalize_anchor_index(-1, nodes, log)

    with pytest.raises(ValueError, match="anchor index out of range"):
        _normalize_anchor_index(5, nodes, log)  # 5 > len(nodes)==1

    # Valid in-range value returns it unchanged
    assert _normalize_anchor_index(1, nodes, log) == 1


def test_parse_transcript_accepts_valid_system_block():
    transcript = """\
## TOAS:SYSTEM
You are an assistant.

## TOAS:USER
hello
"""
    assert parse_transcript(transcript) == [
        {"role": "system", "content": "You are an assistant."},
        {"role": "user", "content": "hello"},
    ]


def test_normalize_indices_none_fallback():
    from toas.transcript import _normalize_anchor_index, _normalize_bind_index

    assert _normalize_bind_index(None, []) == 0
    assert _normalize_anchor_index(None, [], []) == 0


def test_lcp_and_eq_unit_tests():
    from toas.transcript import _eq, _lcp

    assert _eq({"role": "user", "content": "hello"}, {"role": "user", "content": "  hello  "})
    assert not _eq({"role": "user", "content": "hello"}, {"role": "assistant", "content": "hello"})
    assert not _eq({"role": "user", "content": "hello"}, {"role": "user", "content": "hello2"})

    a = [{"role": "user", "content": "hello"}, {"role": "assistant", "content": "hi"}]
    b = [{"role": "user", "content": "hello"}, {"role": "assistant", "content": "hi"}, {"role": "user", "content": "next"}]
    assert _lcp(a, b) == 2

    # LCP breaks early on mismatch
    assert _lcp([{"role": "user", "content": "a"}], [{"role": "user", "content": "b"}]) == 0


def test_parse_transcript_accepts_state_and_state_diff_blocks():
    transcript = """\
## TOAS:STATE/1
state:
  goal: explore

## TOAS:USER
continue

## TOAS:STATE-DIFF/1
state_patch:
  goal: finish
"""
    parsed = parse_transcript(transcript)
    assert parsed == [
        {"role": "state", "content": "state:\n  goal: explore"},
        {"role": "user", "content": "continue"},
        {"role": "state-diff", "content": "state_patch:\n  goal: finish"},
    ]


def test_parse_transcript_preserves_non_canonical_marker_decorations():
    transcript = """\
## TOAS:STATE/2 [turn=2]
state:
  goal: explore
"""
    parsed = parse_transcript(transcript)
    assert parsed == [
        {"role": "state", "content": "state:\n  goal: explore", "marker": "## TOAS:STATE/2 [turn=2]", "turn_id": "2"},
    ]
    # Lossless round-trip preserves custom decoration
    assert render_transcript(parsed) == "## TOAS:STATE/2 [turn=2]\nstate:\n  goal: explore\n"


def test_render_transcript_state_canonical_markers():
    messages = [
        {"role": "state", "content": "state: {goal: a}"},
        {"role": "state-diff", "content": "state_patch: {goal: b}"},
        {"role": "state/2", "content": "state: {goal: c}"},
    ]
    rendered = render_transcript(messages)
    assert rendered == (
        "## TOAS:STATE/1\nstate: {goal: a}\n\n"
        "## TOAS:STATE-DIFF/1\nstate_patch: {goal: b}\n\n"
        "## TOAS:STATE/2\nstate: {goal: c}\n"
    )


def test_state_turn_escaping_and_unescaping_round_trip():
    messages = [
        {
            "role": "assistant",
            "content": "example:\n## TOAS:STATE/1\nstate: {goal: inner}\n## TOAS:STATE-DIFF/1\nend",
        }
    ]
    rendered = render_transcript(messages)
    assert "\\## TOAS:STATE/1" in rendered
    assert "\\## TOAS:STATE-DIFF/1" in rendered
    parsed = parse_transcript(rendered)
    assert parsed == messages


def test_lcp_and_eq_with_state_turns():
    from toas.transcript import _eq, _lcp

    a_state = {"role": "state", "content": "state: {goal: a}"}
    b_state = {"role": "state", "content": "state: {goal: a}", "marker": "## TOAS:STATE/2 [turn=2]"}
    c_state = {"role": "state", "content": "state: {goal: diff}"}

    # Equality and LCP are invariant to presentation decorations
    assert _eq(a_state, b_state)
    assert not _eq(a_state, c_state)

    lineage_a = [a_state, {"role": "user", "content": "run"}]
    lineage_b = [b_state, {"role": "user", "content": "run"}, {"role": "assistant", "content": "done"}]
    assert _lcp(lineage_a, lineage_b) == 2


def test_transcript_telemetry_comment_round_trip_and_lcp_invariance():
    from toas.graph import project_llm_input_from_messages
    from toas.transcript import _eq, _lcp

    transcript = (
        "## TOAS:ASSISTANT\n"
        "<!-- toas: id=alpha target=claude-3-7-sonnet timestamp=2026-11-04T11:41:31Z duration=1.2s -->\n"
        "I am ready to help.\n"
    )
    parsed = parse_transcript(transcript)
    assert len(parsed) == 1
    assert parsed[0]["role"] == "assistant"
    assert parsed[0]["turn_id"] == "alpha"
    assert parsed[0]["content"] == "I am ready to help."
    assert parsed[0]["telemetry_comment"] == "<!-- toas: id=alpha target=claude-3-7-sonnet timestamp=2026-11-04T11:41:31Z duration=1.2s -->"

    # Round trip rendering (spaced and unspaced)
    rendered_unspaced = render_transcript(parsed, spaced=False)
    assert "<!-- toas: id=alpha target=claude-3-7-sonnet" in rendered_unspaced
    rendered_spaced = render_transcript(parsed, spaced=True)
    assert "<!-- toas: id=alpha target=claude-3-7-sonnet" in rendered_spaced

    # LCP and equality invariance with and without telemetry comment
    clean_assistant = {"role": "assistant", "content": "I am ready to help."}
    assert _eq(parsed[0], clean_assistant)
    assert _lcp([parsed[0]], [clean_assistant]) == 1

    # Model input sanitization completely omits telemetry comment
    llm_input = project_llm_input_from_messages(parsed)
    assert len(llm_input) == 1
    assert llm_input[0]["content"] == "I am ready to help."
    assert "toas:" not in llm_input[0]["content"]


def test_transcript_compact_turn_id_parsing_and_invariance():
    from toas.graph import project_llm_input_from_messages
    from toas.transcript import _eq, _lcp

    transcript = (
        "## TOAS:USER [alpha]\n"
        "Please check the SQLite database.\n\n"
        "## TOAS:ASSISTANT [bravo claude-3-7-sonnet 11:42:00 1.2s]\n"
        "I will check [[alpha]] for you.\n"
    )
    parsed = parse_transcript(transcript)
    assert len(parsed) == 2
    assert parsed[0]["turn_id"] == "alpha"
    assert parsed[1]["turn_id"] == "bravo"

    # LCP invariance
    clean_user = {"role": "user", "content": "Please check the SQLite database."}
    clean_assistant = {"role": "assistant", "content": "I will check [[alpha]] for you."}
    assert _eq(parsed[0], clean_user)
    assert _eq(parsed[1], clean_assistant)
    assert _lcp(parsed, [clean_user, clean_assistant]) == 2

    # Round trip preserves marker
    rendered = render_transcript(parsed, spaced=True)
    assert "[alpha]" in rendered
    assert "[bravo claude-3-7-sonnet 11:42:00 1.2s]" in rendered

    # LLM input strips all markers and turn IDs
    llm_input = project_llm_input_from_messages(parsed)
    assert len(llm_input) == 2
    assert "marker" not in llm_input[0]
    assert "turn_id" not in llm_input[0]
    assert "marker" not in llm_input[1]
    assert "turn_id" not in llm_input[1]




