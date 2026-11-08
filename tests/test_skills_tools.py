import pytest

from toas.capability_prompts import (
    _tool_shape_hint,
    _tool_summary,
    render_tool_definitions,
)
from toas.tools import (
    REGISTRY,
    execute_call,
    get_tool,
    validate_call,
)


def test_tool_registry_skill_entry():
    assert "skill" in REGISTRY
    assert "activate_skill" in REGISTRY

    tool = get_tool("skill")
    assert tool.name == "skill"
    assert tool.required_args == ("name",)
    assert tool.optional_args == ("arguments",)

    tool_alt = get_tool("activate_skill")
    assert tool_alt.name == "activate_skill"


def test_execute_skill_tool_success():
    call = {"tool_name": "skill", "args": {"name": "record-task", "arguments": "plan=fix"}}
    tool, args = validate_call(call)
    assert tool.name == "skill"
    assert args["name"] == "record-task"
    assert args["arguments"] == "plan=fix"

    result = execute_call(call)
    assert result["ok"] is True
    assert result["tool_name"] == "skill"
    assert "Activated skill: record-task" in result["summary"]
    assert "# Activated Skill: record-task" in result["content"]
    assert "plan=fix" in result["content"]


def test_execute_activate_skill_tool_success():
    call = {"tool_name": "activate_skill", "args": {"name": "jj-scratch-workspace"}}
    tool, args = validate_call(call)
    assert tool.name == "activate_skill"

    result = execute_call(call)
    assert result["ok"] is True
    assert "jj-scratch-workspace" in result["summary"]


def test_execute_skill_tool_invalid_args():
    with pytest.raises(RuntimeError, match="invalid arguments for tool skill: missing name"):
        validate_call({"tool_name": "skill", "args": {}})

    with pytest.raises(RuntimeError, match="invalid arguments for tool skill: name must be a non-empty string"):
        execute_call({"tool_name": "skill", "args": {"name": ""}})

    with pytest.raises(RuntimeError, match="invalid arguments for tool skill: name must be a non-empty string"):
        execute_call({"tool_name": "skill", "args": {"name": 123}})


def test_execute_skill_tool_not_found():
    with pytest.raises(RuntimeError, match="skill not found: non_existent_skill_xyz"):
        execute_call({"tool_name": "skill", "args": {"name": "non_existent_skill_xyz"}})


def test_capability_prompts_skill_definitions():
    assert "activate an agent skill on-demand" in _tool_summary("skill")
    assert "activate an agent skill on-demand" in _tool_summary("activate_skill")

    hint = _tool_shape_hint("skill")
    assert "operation: skill" in hint
    assert "name: record-task" in hint

    hint_alt = _tool_shape_hint("activate_skill")
    assert "operation: skill" in hint_alt

    # Render tool definitions includes skills catalog when skill is visible
    defs = render_tool_definitions(profile="core")
    assert "- skill (args: name, optional: arguments)" in defs
    assert "Available Skills:" in defs
    assert "record-task" in defs
    assert "```skills block_id=skills_catalog" in defs


def test_dynamic_v2_skills_catalog_block():
    from toas.prompts import _render_v2_dynamic_block

    rendered = _render_v2_dynamic_block(
        "capability/skills-catalog_v1",
        options={},
        capability_profile="core",
        capability_hidden_tools=(),
    )
    assert "Available Skills:" in rendered
    assert "record-task" in rendered
    assert "```skills block_id=skills_catalog" in rendered


def test_execute_skill_tool_non_string_arguments():
    call = {'tool_name': 'skill', 'args': {'name': 'record-task', 'arguments': 123}}
    tool, args = validate_call(call)
    assert tool.name == 'skill'
    assert args['name'] == 'record-task'
    assert args['arguments'] == 123

    result = execute_call(call)
    assert result['ok'] is True
    assert '123' in result['content']
