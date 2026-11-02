"""Standard matcher library for executable grant policies."""
from __future__ import annotations

import fnmatch
from collections.abc import Sequence

from .executable_grants import Matcher


def extract_subcommand(
    argv: Sequence[str],
    *,
    flag_options_with_args: Sequence[str] | None = None,
) -> str | None:
    """Extract the first positional subcommand from argv after argv[0]."""
    if len(argv) <= 1:
        return None

    flags_with_args = set(flag_options_with_args or ())
    skip_next = False

    for token in argv[1:]:
        if skip_next:
            skip_next = False
            continue

        if token in flags_with_args:
            skip_next = True
            continue

        if token.startswith("-"):
            continue

        return token

    return None


def allow_all() -> Matcher:
    """Always allow."""
    def _matcher(_argv: Sequence[str]) -> bool | None:
        return True

    return _matcher


def deny_all() -> Matcher:
    """Always deny."""
    def _matcher(_argv: Sequence[str]) -> bool | None:
        return False

    return _matcher


def deny_flags(*flags: str) -> Matcher:
    """Deny invocation if any prohibited flag is present in argv, else abstain."""
    target_flags = set(flags)

    def _matcher(argv: Sequence[str]) -> bool | None:
        for token in argv[1:]:
            if token in target_flags:
                return False

            if token.startswith("--") and "=" in token:
                flag_name = token.split("=", 1)[0]
                if flag_name in target_flags:
                    return False

            if token.startswith("-") and not token.startswith("--") and len(token) > 2:
                # Bundled short flags, e.g. -rf matching -f or -r
                for char in token[1:]:
                    if f"-{char}" in target_flags:
                        return False

        return None

    return _matcher


def allow_subcommands(
    *subcommands: str,
    flag_options_with_args: Sequence[str] | None = None,
) -> Matcher:
    """Allow invocation if the primary subcommand matches, else abstain."""
    allowed = set(subcommands)

    def _matcher(argv: Sequence[str]) -> bool | None:
        cmd = extract_subcommand(argv, flag_options_with_args=flag_options_with_args)
        if cmd is not None and cmd in allowed:
            return True
        return None

    return _matcher


def deny_subcommands(
    *subcommands: str,
    flag_options_with_args: Sequence[str] | None = None,
) -> Matcher:
    """Deny invocation if the primary subcommand matches, else abstain."""
    denied = set(subcommands)

    def _matcher(argv: Sequence[str]) -> bool | None:
        cmd = extract_subcommand(argv, flag_options_with_args=flag_options_with_args)
        if cmd is not None and cmd in denied:
            return False
        return None

    return _matcher


def allow_pattern(pattern: str) -> Matcher:
    """Allow invocation if the full joined command matches pattern, else abstain."""
    def _matcher(argv: Sequence[str]) -> bool | None:
        full_command = " ".join(argv)
        if fnmatch.fnmatchcase(full_command, pattern):
            return True
        return None

    return _matcher


def deny_pattern(pattern: str) -> Matcher:
    """Deny invocation if the full joined command matches pattern, else abstain."""
    def _matcher(argv: Sequence[str]) -> bool | None:
        full_command = " ".join(argv)
        if fnmatch.fnmatchcase(full_command, pattern):
            return False
        return None

    return _matcher


def all_of(*matchers: Matcher) -> Matcher:
    """Combine matchers requiring all decisions to allow and none to deny."""
    def _matcher(argv: Sequence[str]) -> bool | None:
        has_allow = False
        for m in matchers:
            decision = m(argv)
            if decision is False:
                return False
            if decision is True:
                has_allow = True
        return True if has_allow else None

    return _matcher


def any_of(*matchers: Matcher) -> Matcher:
    """Combine matchers allowing if any allows, denying if none allow but one denies."""
    def _matcher(argv: Sequence[str]) -> bool | None:
        has_deny = False
        for m in matchers:
            decision = m(argv)
            if decision is True:
                return True
            if decision is False:
                has_deny = True
        return False if has_deny else None

    return _matcher


def not_matcher(matcher: Matcher) -> Matcher:
    """Invert boolean decision of a matcher, preserving None."""
    def _matcher(argv: Sequence[str]) -> bool | None:
        decision = matcher(argv)
        if decision is None:
            return None
        return not decision

    return _matcher
