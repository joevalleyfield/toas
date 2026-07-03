from __future__ import annotations


HEADS_USAGE = (
    "usage: toas heads [--sources <hot|segments|path> ...]\n"
    "show the selected history graph leaf set as a compact branch-tip view\n"
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
