from __future__ import annotations

import yaml

from toas.runtime.frontier_resolution import extract_frontier_assistant_candidates
from toas.runtime.yaml_healing import heal_candidate_yaml


def test_heal_candidate_yaml_empty_or_invalid_inputs():
    assert heal_candidate_yaml("") is None
    assert heal_candidate_yaml("   \n\t  ") is None
    assert heal_candidate_yaml(None) is None  # type: ignore[arg-type]


def test_heal_candidate_yaml_clean_valid_block():
    block = (
        "- operation: replace_block\n"
        "  arguments:\n"
        "    path: foo.py\n"
        "    search_block: |\n"
        "      hello\n"
        "    replacement_block: |\n"
        "      world\n"
    )
    healed = heal_candidate_yaml(block)
    assert healed is not None
    parsed = yaml.safe_load(healed)
    assert parsed[0]["operation"] == "replace_block"
    assert parsed[0]["arguments"]["search_block"] == "hello\n"
    assert parsed[0]["arguments"]["replacement_block"] == "world\n"


def test_heal_candidate_yaml_outdented_arguments_under_list_item():
    block = (
        "- operation: replace_block\n"
        "arguments:\n"
        "path: foo.py\n"
        "search_block: |\n"
        "  line 1\n"
        "  line 2\n"
        "replacement_block: |\n"
        "  line 1\n"
    )
    healed = heal_candidate_yaml(block)
    assert healed is not None
    parsed = yaml.safe_load(healed)
    assert isinstance(parsed, list)
    assert parsed[0]["operation"] == "replace_block"
    assert parsed[0]["arguments"]["path"] == "foo.py"
    assert parsed[0]["arguments"]["search_block"] == "line 1\nline 2\n"
    assert parsed[0]["arguments"]["replacement_block"] == "line 1\n"


def test_heal_candidate_yaml_bare_mapping_with_outdented_subkeys():
    block = (
        "operation: replace_block\n"
        "arguments:\n"
        "path: foo.py\n"
        "search_block: |\n"
        "  line 1\n"
        "replacement_block: |\n"
        "  line 1\n"
    )
    healed = heal_candidate_yaml(block)
    assert healed is not None
    parsed = yaml.safe_load(healed)
    assert isinstance(parsed, dict)
    assert parsed["operation"] == "replace_block"
    assert parsed["arguments"]["path"] == "foo.py"


def test_heal_candidate_yaml_sibling_indent_search_block():
    # search_block: | has code lines at same indentation as search_block
    block = (
        "- operation: replace_block\n"
        "  arguments:\n"
        "    path: foo.py\n"
        "    search_block: |\n"
        "    def foo():\n"
        "        pass\n"
        "    replacement_block: |\n"
        "    def foo():\n"
        "        return 42\n"
    )
    healed = heal_candidate_yaml(block)
    assert healed is not None
    parsed = yaml.safe_load(healed)
    assert parsed[0]["arguments"]["search_block"] == "def foo():\n    pass\n"
    assert parsed[0]["arguments"]["replacement_block"] == "def foo():\n    return 42\n"


def test_heal_candidate_yaml_internal_outdent_requires_indent_indicator():
    # First line indented by 4, subsequent line indented by 0 (top-level function or comment),
    # including an empty blank line in between.
    block = (
        "- operation: replace_block\n"
        "  arguments:\n"
        "    path: foo.py\n"
        "    search_block: |\n"
        "        def bar():\n"
        "\n"
        "            pass\n"
        "    def baz():\n"
        "        return 1\n"
        "    replacement_block: |\n"
        "        def bar():\n"
        "            return 2\n"
    )
    healed = heal_candidate_yaml(block)
    assert healed is not None
    parsed = yaml.safe_load(healed)
    assert "def baz():\n    return 1\n" in parsed[0]["arguments"]["search_block"]
    assert "    def bar():\n\n        pass" in parsed[0]["arguments"]["search_block"]
    assert parsed[0]["arguments"]["replacement_block"].strip() == "def bar():\n    return 2"


def test_heal_candidate_yaml_preserves_nested_code_matching_delim_names():
    # Code inside search_block has a nested type annotation matching a tool argument name `path:`
    block = (
        "- operation: replace_block\n"
        "  arguments:\n"
        "    path: foo.py\n"
        "    search_block: |\n"
        "      class Item:\n"
        "          path: str = 'nested'\n"
        "    replacement_block: |\n"
        "      class Item:\n"
        "          path: Path = Path('nested')\n"
    )
    healed = heal_candidate_yaml(block)
    assert healed is not None
    parsed = yaml.safe_load(healed)
    assert "path: str = 'nested'" in parsed[0]["arguments"]["search_block"]
    assert "path: Path = Path('nested')" in parsed[0]["arguments"]["replacement_block"]


def test_heal_candidate_yaml_chomper_variants():
    block_strip = (
        "operation: replace_block\n"
        "arguments:\n"
        "  search_block: |-\n"
        "    hello\n"
        "  replacement_block: |+\n"
        "    world\n"
        "  content: >\n"
        "    some text\n"
    )
    healed = heal_candidate_yaml(block_strip)
    assert healed is not None
    parsed = yaml.safe_load(healed)
    assert parsed["arguments"]["search_block"] == "hello"
    assert parsed["arguments"]["replacement_block"] == "world\n"
    assert "some text" in parsed["arguments"]["content"]


def test_heal_candidate_yaml_empty_scalar_body():
    block = "operation: replace_block\narguments:\n  search_block: |\n  replacement_block: |\n"
    healed = heal_candidate_yaml(block)
    assert healed is not None
    parsed = yaml.safe_load(healed)
    assert parsed["arguments"]["search_block"] is None or parsed["arguments"]["search_block"] == ""


def test_heal_candidate_yaml_unhealable_returns_none():
    block = "- operation: replace_block\n  arguments: { [ bad yaml : [ } }\n"
    assert heal_candidate_yaml(block) is None


def test_extract_frontier_assistant_candidates_recovers_healed_yaml():
    content = (
        "Here is the change:\n"
        "```yaml\n"
        "- operation: replace_block\n"
        "arguments:\n"
        "path: src/main.py\n"
        "search_block: |\n"
        "def run():\n"
        "    pass\n"
        "replacement_block: |\n"
        "def run():\n"
        "    print('hello')\n"
        "```\n"
    )
    candidates, skipped = extract_frontier_assistant_candidates(content)
    assert len(candidates) == 1
    assert skipped == []
    cand = candidates[0]
    assert cand["kind"] == "tool_plan"
    assert "replace_block" in cand["preview"]


def test_extract_frontier_assistant_candidates_healed_invalid_call_skipped():
    # Heals structurally to YAML, but tool_plan item fails validation (unknown operation)
    content = (
        "```yaml\n"
        "- operation: nonexistent_custom_tool\n"
        "arguments:\n"
        "path: src/main.py\n"
        "search_block: |\n"
        "hello\n"
        "```\n"
    )
    candidates, skipped = extract_frontier_assistant_candidates(content)
    assert len(candidates) == 0
    assert len(skipped) == 1
    assert "yaml parse error" in skipped[0]
