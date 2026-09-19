from __future__ import annotations

from toas.runtime.rendering_edges import render_transcript_blocks
from toas.step import step


def _result_nodes(transcript: str) -> list[dict]:
    _new_nodes, results = step(transcript, [])
    return results


def test_multi_tool_plan_projection_preserves_order_and_exactly_once_blocks() -> None:
    results = _result_nodes(
        """\
## TOAS:USER
```yaml
- operation: echo
  arguments:
    text: alpha
- operation: echo
  arguments:
    text: beta
```
"""
    )

    assert [node["content"] for node in results] == ["[OK] echo: alpha", "[OK] echo: beta"]
    projection = render_transcript_blocks(results)
    assert projection.count("[OK] echo: alpha") == 1
    assert projection.count("[OK] echo: beta") == 1
    assert projection.index("[OK] echo: alpha") < projection.index("[OK] echo: beta")
    assert all(node["projection_lane"] == "user" for node in results)


def test_explicit_user_shell_result_is_user_scoped_and_renderable() -> None:
    results = _result_nodes("## TOAS:USER\n\n$ printf shell-contract\n")

    assert len(results) == 1
    result = results[0]
    assert result["origin_role"] == "user"
    assert result["origin_kind"] == "user_shell"
    assert result["projection_lane"] == "user"
    assert "shell-contract" in result["content"]
    projection = render_transcript_blocks(results)
    assert projection.startswith("## TOAS:USER\n\n## RESULT\n")
    assert "shell-contract" in projection


def test_policy_or_validation_failure_remains_a_canonical_projection() -> None:
    results = _result_nodes(
        """\
## TOAS:USER
```yaml
- tool_name: shell_script
  args:
    script: ""
```
"""
    )

    assert len(results) == 1
    assert results[0]["content"].startswith("[ERROR] shell_script:")
    assert results[0]["projection_lane"] == "user"
    projection = render_transcript_blocks(results)
    assert projection.count("## RESULT") == 1
    assert "[ERROR] shell_script:" in projection
