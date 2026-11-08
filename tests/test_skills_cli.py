from pathlib import Path
from unittest.mock import MagicMock

import pytest

from toas.cli_dispatch import DispatchDeps, dispatch_main
from toas.cli_surface_commands import (
    run_skill as run_surface_skill,
)
from toas.cli_surface_commands import (
    run_skills as run_surface_skills,
)
from toas.cli_usage import SKILL_USAGE, SKILLS_USAGE, get_subcommand_help
from toas.operator_api import (
    SkillOutcome,
    SkillsListOutcome,
    skill_text,
    skills_list_lines,
)
from toas.runtime.request_ops import run_op_capture_stdout


def test_operator_skill_text_success():
    outcome = skill_text(name="record-task")
    assert outcome.name == "record-task"
    assert "Flexible repository task recording" in outcome.description
    assert outcome.scope == "bundled"
    assert "record_task.py" in str(outcome.scripts)
    assert "Skill: record-task" in outcome.text
    assert "--- Instructions ---" in outcome.text


def test_operator_skill_text_not_found():
    with pytest.raises(RuntimeError, match="skill not found: non-existent-skill"):
        skill_text(name="non-existent-skill")


def test_operator_skills_list_lines():
    out_all = skills_list_lines()
    assert len(out_all.skills) >= 3
    assert any(s["name"] == "record-task" for s in out_all.skills)
    assert any("Discovered Skills:" in line for line in out_all.lines)

    # Filter matching
    out_filtered = skills_list_lines(filter_text="scratch")
    assert len(out_filtered.skills) == 1
    assert out_filtered.skills[0]["name"] == "jj-scratch-workspace"

    # Filter not matching
    out_none = skills_list_lines(filter_text="definitely_does_not_exist_xyz")
    assert len(out_none.skills) == 0
    assert "No skills matched filter: 'definitely_does_not_exist_xyz'" in out_none.lines[0]


def test_cli_surface_commands():
    printed: list[str] = []

    def mock_print(val, **kw):
        printed.append(str(val))

    run_surface_skill(
        operator_skill_text=lambda name: SkillOutcome(
            name=name,
            description="desc",
            scope="bundled",
            path="/p",
            aliases=("/" + name,),
            scripts=(),
            content="content",
            text=f"Rendered {name}",
        ),
        name="test-s",
        print_fn=mock_print,
    )
    assert "Rendered test-s" in printed

    printed.clear()
    run_surface_skills(
        operator_skills_list_lines=lambda filter_text: SkillsListOutcome(
            skills=(),
            lines=(f"Skills for {filter_text}",),
        ),
        filter_text="foo",
        print_fn=mock_print,
    )
    assert "Skills for foo" in printed


def test_cli_dispatch_skill_and_skills():
    mock_run_skill = MagicMock()
    mock_run_skills = MagicMock()

    deps = DispatchDeps(
        run_help=MagicMock(),
        run_step=MagicMock(),
        run_step_async=MagicMock(),
        run_watch=MagicMock(),
        run_cancel=MagicMock(),
        run_backend=MagicMock(),
        run_heads=MagicMock(),
        run_intents=MagicMock(),
        run_graph=MagicMock(),
        run_transcript=MagicMock(),
        run_llm_input=MagicMock(),
        run_prompt=MagicMock(),
        run_prompts=MagicMock(),
        run_history=MagicMock(),
        run_session_path=MagicMock(),
        run_surface=MagicMock(),
        run_ancestry=MagicMock(),
        run_diff=MagicMock(),
        run_index_rebuild=MagicMock(),
        run_daemon=MagicMock(),
        run_host=MagicMock(),
        run_replay_script=MagicMock(),
        run_debug_cancel_latency=MagicMock(),
        run_skill=mock_run_skill,
        run_skills=mock_run_skills,
    )

    dispatch_main(["skill", "record-task"], deps=deps)
    mock_run_skill.assert_called_once_with("record-task")

    with pytest.raises(SystemExit, match="usage: toas skill <name>"):
        dispatch_main(["skill"], deps=deps)

    dispatch_main(["skills"], deps=deps)
    mock_run_skills.assert_called_with(None)

    dispatch_main(["skills", "filter-term"], deps=deps)
    mock_run_skills.assert_called_with("filter-term")


def test_cli_usage_help():
    assert get_subcommand_help("skill") == SKILL_USAGE
    assert get_subcommand_help("skills") == SKILLS_USAGE


def test_request_ops_skill_and_skills():
    cli_mod = MagicMock()
    cli_mod.run_skill = MagicMock(return_value="skill-out")
    cli_mod.run_skills = MagicMock(return_value="skills-out")

    def capture(fn, *args, **kwargs):
        fn(*args, **kwargs)
        return "captured"

    res_skill = run_op_capture_stdout("skill", {"name": "record-task"}, cli_module=cli_mod, capture_stdout=capture)
    assert res_skill == "captured"
    cli_mod.run_skill.assert_called_once_with("record-task")

    res_skills = run_op_capture_stdout("skills", {"filter": "task"}, cli_module=cli_mod, capture_stdout=capture)
    assert res_skills == "captured"
    cli_mod.run_skills.assert_called_once_with("task")


def test_cli_module_run_skill_and_skills(monkeypatch, capsys):
    import toas.cli as cli

    monkeypatch.setattr(cli, "_rpc_stdout", lambda op, payload: False)

    cli.run_skill("record-task")
    captured = capsys.readouterr().out
    assert "Skill: record-task" in captured

    cli.run_skills("scratch")
    captured_skills = capsys.readouterr().out
    assert "jj-scratch-workspace" in captured_skills


def test_cli_module_run_skill_and_skills_rpc(monkeypatch):
    import toas.cli as cli

    called = []
    monkeypatch.setattr(cli, '_rpc_stdout', lambda op, payload: called.append((op, payload)) or True)

    cli.run_skill('record-task')
    assert called == [('skill', {'name': 'record-task'})]

    called.clear()
    cli.run_skills('filter')
    assert called == [('skills', {'filter': 'filter'})]


def test_operator_skills_list_lines_shadowed_and_collisions():
    from toas.skills.discovery import Skill, SkillCatalog, SkillRecord

    s1 = Skill(name='s1', path=Path('/p1'), scope='workspace', description='s1 desc', aliases=('/s1',), content='', skill_dir=Path('/d1'))
    s2 = Skill(name='s2', path=Path('/p2'), scope='bundled', description='s2 desc', aliases=('/s2',), content='', skill_dir=Path('/d2'))

    rec1 = SkillRecord(
        skill=s1,
        is_active=True,
        shadows=('/p2',),
        alias_collisions=('/conflict',),
    )
    rec2 = SkillRecord(
        skill=s2,
        is_active=False,
        shadowed_by='/p1',
        alias_collisions=(),
    )
    catalog = SkillCatalog(skills={'s1': s1}, aliases={'s1': 's1'}, records=[rec1, rec2])
    res = skills_list_lines(catalog=catalog)
    joined = chr(10).join(res.lines)
    assert 'shadows: 1 lower-priority' in joined
    assert 'shadowed by /p1' in joined
    assert 'alias collisions: /conflict' in joined
