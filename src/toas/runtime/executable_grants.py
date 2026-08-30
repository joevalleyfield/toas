"""Ordered executable grant evaluation for assistant-directed runtimes."""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

Matcher = Callable[[Sequence[str]], bool | None]


@dataclass(frozen=True)
class ExecutableGrantDecision:
    """The result of evaluating one resolved executable invocation."""

    allowed: bool
    source: str
    prefix: str | None = None
    matcher_index: int | None = None


@dataclass(frozen=True)
class ExecutableGrantPolicy:
    """An ordered, prefix-indexed policy over resolved executable argv."""

    default: bool = False
    prefix_matchers: Mapping[str, Sequence[Matcher]] | None = None

    def evaluate(self, argv: Sequence[str]) -> ExecutableGrantDecision:
        """Evaluate matchers in order, stopping at the first decision."""
        if not argv or not all(isinstance(part, str) and part for part in argv):
            raise ValueError("argv must be a non-empty sequence[str]")

        prefix = argv[0]
        matchers = (self.prefix_matchers or {}).get(prefix, ())
        for matcher_index, matcher in enumerate(matchers):
            decision = matcher(argv)
            if decision is None:
                continue
            if not isinstance(decision, bool):
                raise TypeError("executable grant matcher must return bool or None")
            return ExecutableGrantDecision(
                allowed=decision,
                source="matcher",
                prefix=prefix,
                matcher_index=matcher_index,
            )

        return ExecutableGrantDecision(
            allowed=self.default,
            source="default",
            prefix=prefix,
        )


def evaluate_executable_grant(
    argv: Sequence[str],
    *,
    default: bool = False,
    prefix_matchers: Mapping[str, Sequence[Matcher]] | None = None,
) -> ExecutableGrantDecision:
    """Evaluate an invocation without requiring callers to construct a policy."""
    return ExecutableGrantPolicy(
        default=default,
        prefix_matchers=prefix_matchers,
    ).evaluate(argv)
