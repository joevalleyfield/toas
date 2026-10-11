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


STEP_USAGE = (
    "usage: toas step [--preview-request] [--preview-request-pretty] "
    "[--preview-response] [--stdin] "
    "[--infer-from <state-label>] [--control <slash_command>] "
    "[--session <transcript_path>] [--surface <surface_id>]\n"
    "Run 'toas step --help' for details and examples."
)


STEP_ASYNC_USAGE = "usage: toas step --async [--session <transcript_path>] [--surface <surface_id>]"


STEP_HELP = (
    "usage: toas step [options]\n\n"
    "Step session history: synchronize transcript edits into durable history,\n"
    "execute pending tool requests or control directives at the frontier, and\n"
    "run model inference.\n\n"
    "Input & Ingress:\n"
    "  --session <path>          Path to transcript file (default: session.md).\n"
    "  --stdin                   Read appended transcript content from standard input.\n"
    "  --control <slash_command> Inject and execute a control command turn at the frontier\n"
    "                            (e.g. --control /run or --control \"/session show\").\n\n"
    "Inspection & Previews:\n"
    "  --preview-request         Print model-input request messages without invoking the model.\n"
    "                            (Alias: --preview. Requires a typed state turn.)\n"
    "  --preview-request-pretty  Print the same model-input request messages with stringified\n"
    "                            JSON payloads unpacked for near-literal human inspection.\n"
    "                            (Implies --preview-request. Requires a typed state turn.)\n"
    "  --preview-response        Invoke the model and print raw response content without\n"
    "                            writing results to transcript or durable history.\n"
    "                            (Requires a typed state turn.)\n\n"
    "Trajectory Steering:\n"
    "  --infer-from <label>      Branch inference from a historical state milestone\n"
    "                            (e.g. --infer-from STATE/1). Requires a typed state transcript.\n\n"
    "Deprecated:\n"
    "  --async                   Spawns daemon RPC background task. Deprecated; prefer\n"
    "                            'toas host serve' stdio protocol instead.\n"
    "  --surface <surface_id>    Target session by bound surface ID. Deprecated; prefer\n"
    "                            direct '--session <path>' targeting.\n\n"
    "Notes:\n"
    "  - Stepping adheres to strict phase ordering: frontier user/control intent is\n"
    "    resolved first, tool calls execute second, and model inference occurs third.\n"
    "  - In a typed state transcript, edit 'state' and optionally add a 'user_tool_calls'\n"
    "    array. Stepping consolidates state edits and executes user tool calls before\n"
    "    prompting the model with resulting state and observations.\n\n"
    "Examples:\n"
    "  toas step                                 # Synchronize and step current session.md\n"
    "  toas step --session .toas/session-task.md # Step explicit session file\n"
    "  cat turn.md | toas step --stdin           # Append turn from stdin and step\n"
    "  toas step --preview-request               # Inspect projected prompt without calling model\n"
    "  toas step --infer-from STATE/2            # Step from explicit prior state milestone"
)


SESSION_CONTINUE_USAGE = (
    "usage: toas session continue [--predecessor <transcript_path>] "
    "[--name <session_name>] [--ignore-preceding-graph] [--exclude-tail]"
)


SURFACE_USAGE = "usage: toas surface [list|bind|select|rebind] ..."


WATCH_USAGE = "usage: toas watch <run_id> [--offset <n>] [--follow]"


CANCEL_USAGE = "usage: toas cancel <run_id>"


BACKEND_USAGE = "usage: toas backend [start|stop|restart|status]"


INTENTS_USAGE = "usage: toas intents"


PROMPT_USAGE = "usage: toas prompt <ref> [--mode <direct|mimic>] [--constraint <name> ...]"


PROMPTS_USAGE = "usage: toas prompts [prefix]"


SESSION_PATH_USAGE = "usage: toas session-path"


ANCESTRY_USAGE = "usage: toas ancestry <message_id> [--depth <n>] [--full]"


DIFF_USAGE = "usage: toas diff <head_a> <head_b> [--full]"


INDEX_USAGE = "usage: toas index [rebuild]"


DAEMON_USAGE = "usage: toas daemon [start|stop|status]"


HOST_USAGE = "usage: toas host serve [--owner-pid <pid>]"


REPLAY_SCRIPT_USAGE = "usage: toas replay-script <script_path> [--output <path>] [--dry-run]"


DEBUG_USAGE = "usage: toas debug cancel-latency <jsonl_path>"


_SUBCOMMAND_HELP: dict[str, str] = {
    "step": STEP_HELP,
    "heads": HEADS_USAGE,
    "history": HISTORY_USAGE,
    "graph": GRAPH_USAGE,
    "transcript": TRANSCRIPT_USAGE,
    "llm-input": LLM_INPUT_USAGE,
    "session": SESSION_CONTINUE_USAGE,
    "surface": SURFACE_USAGE,
    "watch": WATCH_USAGE,
    "cancel": CANCEL_USAGE,
    "backend": BACKEND_USAGE,
    "intents": INTENTS_USAGE,
    "prompt": PROMPT_USAGE,
    "prompts": PROMPTS_USAGE,
    "session-path": SESSION_PATH_USAGE,
    "ancestry": ANCESTRY_USAGE,
    "diff": DIFF_USAGE,
    "index": INDEX_USAGE,
    "daemon": DAEMON_USAGE,
    "service": DAEMON_USAGE,
    "host": HOST_USAGE,
    "transport": HOST_USAGE,
    "replay-script": REPLAY_SCRIPT_USAGE,
    "debug": DEBUG_USAGE,
}


def get_subcommand_help(command: str) -> str | None:
    return _SUBCOMMAND_HELP.get(command)

