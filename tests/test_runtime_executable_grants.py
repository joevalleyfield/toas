from __future__ import annotations

import pytest

from toas.runtime.executable_grants import ExecutableGrantPolicy, evaluate_executable_grant


def test_matchers_are_ordered_and_stop_at_first_decision():
    calls: list[str] = []

    def abstain(argv):
        calls.append(f"abstain:{argv[0]}")
        return None

    def allow(argv):
        calls.append(f"allow:{argv[1]}")
        return True

    def should_not_run(argv):
        calls.append("unexpected")
        return False

    decision = ExecutableGrantPolicy(
        prefix_matchers={"uv": (abstain, allow, should_not_run)},
    ).evaluate(("uv", "run", "pytest"))

    assert decision.allowed is True
    assert decision.source == "matcher"
    assert decision.prefix == "uv"
    assert decision.matcher_index == 1
    assert calls == ["abstain:uv", "allow:run"]


def test_explicit_deny_can_precede_allow_all_with_default_deny():
    def deny_pytest(argv):
        return False if argv[1:] == ("run", "pytest") else None

    def allow_all(argv):
        return True

    policy = ExecutableGrantPolicy(
        default=False,
        prefix_matchers={"uv": (deny_pytest, allow_all)},
    )

    assert policy.evaluate(("uv", "run", "pytest")).allowed is False
    assert policy.evaluate(("uv", "run", "python")).allowed is True


def test_default_allow_supports_blacklist_and_unmatched_prefix_uses_default():
    def deny_network(argv):
        return False if "--network" in argv else None

    policy = ExecutableGrantPolicy(
        default=True,
        prefix_matchers={"uv": (deny_network,)},
    )

    assert policy.evaluate(("uv", "run", "python")).allowed is True
    assert policy.evaluate(("uv", "run", "python", "--network")).allowed is False
    assert policy.evaluate(("jj", "status")).allowed is True


def test_helper_evaluates_a_prefix_indexed_policy():
    decision = evaluate_executable_grant(
        ("jj", "status"),
        prefix_matchers={"jj": (lambda argv: True,)},
    )

    assert decision == decision.__class__(allowed=True, source="matcher", prefix="jj", matcher_index=0)


@pytest.mark.parametrize("argv", [(), ("",), ("uv", "")])
def test_evaluator_rejects_invalid_argv(argv):
    with pytest.raises(ValueError, match=r"argv must be a non-empty sequence\[str\]"):
        ExecutableGrantPolicy().evaluate(argv)


def test_evaluator_rejects_invalid_matcher_decision():
    with pytest.raises(TypeError, match="must return bool or None"):
        ExecutableGrantPolicy(prefix_matchers={"uv": (lambda argv: "allow",)}).evaluate(("uv",))
