"""Tests for the standard matcher library."""
from __future__ import annotations

from toas.runtime.executable_grants import ExecutableGrantPolicy
from toas.runtime.matchers import (
    all_of,
    allow_all,
    allow_pattern,
    allow_subcommands,
    any_of,
    deny_all,
    deny_flags,
    deny_pattern,
    deny_subcommands,
    extract_subcommand,
    not_matcher,
)


def test_extract_subcommand():
    assert extract_subcommand(["git"]) is None
    assert extract_subcommand([]) is None
    assert extract_subcommand(["git", "status"]) == "status"
    assert extract_subcommand(["git", "--no-pager", "diff"]) == "diff"
    assert (
        extract_subcommand(
            ["git", "-C", "/tmp", "--no-pager", "log"],
            flag_options_with_args=["-C"],
        )
        == "log"
    )
    assert extract_subcommand(["git", "-C"]) is None


def test_allow_all_and_deny_all():
    assert allow_all()(["ls", "-la"]) is True
    assert deny_all()(["ls", "-la"]) is False


def test_deny_flags():
    m = deny_flags("--network", "--force", "-f")
    assert m(["git", "push", "--force"]) is False
    assert m(["git", "push", "--network=none"]) is False
    assert m(["rm", "-rf", "/tmp/foo"]) is False
    assert m(["git", "status"]) is None
    assert m(["git", "--no-pager", "diff"]) is None


def test_allow_subcommands():
    m = allow_subcommands("status", "diff", "log")
    assert m(["git", "status"]) is True
    assert m(["git", "--no-pager", "diff"]) is True
    assert m(["git", "push"]) is None
    assert m(["git"]) is None


def test_deny_subcommands():
    m = deny_subcommands("push", "reset", "clean")
    assert m(["git", "push", "origin", "main"]) is False
    assert m(["git", "reset", "--hard"]) is False
    assert m(["git", "status"]) is None
    assert m(["git"]) is None


def test_allow_and_deny_pattern():
    m_allow = allow_pattern("git log *")
    assert m_allow(["git", "log", "-n", "5"]) is True
    assert m_allow(["git", "status"]) is None

    m_deny = deny_pattern("rm -rf *")
    assert m_deny(["rm", "-rf", "/"]) is False
    assert m_deny(["rm", "file.txt"]) is None


def test_all_of():
    m = all_of(deny_flags("--force"), allow_subcommands("push", "commit"))
    # Push without force: deny_flags -> None, allow_subcommands -> True => True
    assert m(["git", "push"]) is True
    # Push with force: deny_flags -> False => False
    assert m(["git", "push", "--force"]) is False
    # Status: deny_flags -> None, allow_subcommands -> None => None
    assert m(["git", "status"]) is None

    # Empty all_of
    assert all_of()(["git"]) is None


def test_any_of():
    m = any_of(allow_subcommands("status"), deny_subcommands("push"))
    assert m(["git", "status"]) is True
    assert m(["git", "push"]) is False
    assert m(["git", "checkout"]) is None

    # Empty any_of
    assert any_of()(["git"]) is None


def test_not_matcher():
    m = not_matcher(deny_flags("--force"))
    assert m(["git", "push", "--force"]) is True
    assert m(["git", "status"]) is None

    m2 = not_matcher(allow_all())
    assert m2(["ls"]) is False


def test_policy_composition_with_standard_matchers():
    policy = ExecutableGrantPolicy(
        default=False,
        prefix_matchers={
            "git": (
                deny_flags("--force", "-f"),
                allow_subcommands("status", "diff", "log"),
            ),
            "uv": (
                deny_flags("--upgrade"),
                allow_subcommands("run"),
            ),
        },
    )

    # git status allowed by matcher
    d1 = policy.evaluate(["git", "status"])
    assert d1.allowed is True
    assert d1.source == "matcher"

    # git push falls through to default=False
    d2 = policy.evaluate(["git", "push"])
    assert d2.allowed is False
    assert d2.source == "default"

    # git diff --force denied by matcher
    d3 = policy.evaluate(["git", "diff", "--force"])
    assert d3.allowed is False
    assert d3.source == "matcher"
