"""Reconciliation handoff shape: transcript → operator semantics boundary.

This module owns the explicit data contract between transcript reconciliation
(LCP, bind, anchor, new node extraction) and operator semantics (consequence
selection, execution, generation).

Invariants:
- divergence_parent is None for linear continuation, set for branch
- refusal is set when reconciliation cannot produce a frontier
- diagnostics captures provenance decisions made during reconciliation
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ReconciliationDiagnostics:
    """Structured provenance decisions from reconciliation."""
    corrections: dict[int, str] = field(default_factory=dict)
    """Map from new-from-transcript index to the id of the corrected node."""
    uncertain: set[int] = field(default_factory=set)
    """Set of new-from-transcript indices with uncertain provenance."""
    parsed_nodes_len: int = 0
    bound_log_len: int = 0
    new_from_transcript_len: int = 0


@dataclass(frozen=True)
class RefusalReason:
    """Reason reconciliation refused to produce a frontier."""
    code: str
    detail: str


@dataclass(frozen=True)
class ReconciliationHandoff:
    """Explicit handoff from transcript reconciliation to operator semantics.

    Reconciliation produces this shape; operator semantics consumes it.
    No sidecar state or implicit boundary crossings.
    """
    # --- Reconciled state ---
    working_for_frontier: list[dict]
    """Working message list for operator consequence selection."""
    new_from_transcript: list[dict]
    """New nodes extracted from transcript, to be recorded as durable history."""
    frontier: dict | None
    """Selected frontier node (last element of working_for_frontier)."""

    # --- Branch decision ---
    divergence_parent: str | None
    """Parent node id from which divergence occurs.
    None for linear continuation; set when branch is needed."""

    # --- Reconciliation metadata ---
    bind_index: int
    lcp_index: int

    # --- Diagnostics ---
    diagnostics: ReconciliationDiagnostics | None = None
    refusal: RefusalReason | None = None