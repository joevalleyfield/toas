from __future__ import annotations

HEADS_USAGE = (
    "usage: toas heads [--sources <hot|segments|path> ...]\n"
    "show the selected history graph leaf set as a compact branch-tip view\n"
    "zero-arg scope is hot history\n"
    "use `--sources` to select explicit event-log sources"
)


HISTORY_USAGE = (
    "usage: toas history [limit] [anchor] [--sources <hot|segments|path> ...]\n"
    "show the current root-to-head lineage as a bounded readable window\n"
    "zero-arg scope follows the shared implicit anchor: the current default lineage\n"
    "use `--sources` to select explicit event-log sources"
)


TRANSCRIPT_USAGE = (
    "usage: toas transcript [anchor] [--sources <hot|segments|path> ...]\n"
    "show transcript projection for a selected lineage\n"
    "zero-arg scope is hot history\n"
    "use `--sources` to select explicit event-log sources"
)


LLM_INPUT_USAGE = (
    "usage: toas llm-input [anchor] [--sources <hot|segments|path> ...] [--envelope]\n"
    "show the model-input projection for a selected lineage\n"
    "zero-arg scope is hot history\n"
    "use `--sources` to select explicit event-log sources"
)


GRAPH_USAGE = (
    "usage: toas graph [anchor] [-N] [+N] [--projection temporal|consequence] "
    "[--sources <hot|segments|path> ...] [--stitch-diagnostics]\n"
    "show the selected history graph as a topology view across hot history by default\n"
    "use an anchor plus -N/+N to render a bounded local neighborhood\n"
    "use `--sources` to select explicit event-log sources"
)
