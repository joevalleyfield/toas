from __future__ import annotations


STEP_USAGE = "usage: toas step [--stdin] [--control <slash_command>] [--session <transcript_path>] [--surface <surface_id>]"
STEP_ASYNC_USAGE = "usage: toas step --async [--session <transcript_path>] [--surface <surface_id>]"
SURFACE_USAGE = "usage: toas surface [list|bind|select|rebind] ..."
SURFACE_BIND_USAGE = "usage: toas surface bind <surface_id> <transcript_path> [--reason <text>]"
SURFACE_SELECT_USAGE = "usage: toas surface select <surface_id>"
SURFACE_REBIND_USAGE = "usage: toas surface rebind <surface_id> --from-head <head_id> --to-head <head_id> --reason <text>"
GRAPH_USAGE = "usage: toas graph [--projection temporal|consequence]"


def parse_step_options(argv: list[str]) -> tuple[bool, str | None, str | None, str | None]:
    stdin_mode = False
    control: str | None = None
    session_path: str | None = None
    surface_id: str | None = None
    i = 1
    while i < len(argv):
        arg = argv[i]
        if arg == "--stdin":
            stdin_mode = True
            i += 1
            continue
        if arg == "--control":
            if i + 1 >= len(argv):
                raise SystemExit(STEP_USAGE)
            control = argv[i + 1]
            i += 2
            continue
        if arg == "--session":
            if i + 1 >= len(argv):
                raise SystemExit(STEP_USAGE)
            session_path = argv[i + 1]
            i += 2
            continue
        if arg == "--surface":
            if i + 1 >= len(argv):
                raise SystemExit(STEP_USAGE)
            surface_id = argv[i + 1]
            i += 2
            continue
        raise SystemExit(f"unknown option: {arg}")
    return stdin_mode, control, session_path, surface_id


def parse_step_async_options(argv: list[str]) -> tuple[str | None, str | None]:
    session_path: str | None = None
    surface_id: str | None = None
    i = 2
    while i < len(argv):
        arg = argv[i]
        if arg == "--session":
            if i + 1 >= len(argv):
                raise SystemExit(STEP_ASYNC_USAGE)
            session_path = argv[i + 1]
            i += 2
            continue
        if arg == "--surface":
            if i + 1 >= len(argv):
                raise SystemExit(STEP_ASYNC_USAGE)
            surface_id = argv[i + 1]
            i += 2
            continue
        raise SystemExit(f"unknown option: {arg}")
    return session_path, surface_id


def parse_surface_options(argv: list[str]) -> tuple[str, tuple[str, ...], str | None]:
    if len(argv) < 2:
        raise SystemExit(SURFACE_USAGE)
    sub = argv[1]
    if sub == "list":
        return "list", tuple(), None
    if sub == "bind":
        if len(argv) < 4:
            raise SystemExit(SURFACE_BIND_USAGE)
        reason = None
        if len(argv) > 4:
            if len(argv) != 6 or argv[4] != "--reason":
                raise SystemExit(SURFACE_BIND_USAGE)
            reason = argv[5]
        return "bind", (argv[2], argv[3]), reason
    if sub == "select":
        if len(argv) < 3:
            raise SystemExit(SURFACE_SELECT_USAGE)
        return "select", (argv[2],), None
    if sub == "rebind":
        if len(argv) < 3:
            raise SystemExit(SURFACE_REBIND_USAGE)
        surface_id = argv[2]
        from_head_id = None
        to_head_id = None
        reason = None
        i = 3
        while i < len(argv):
            arg = argv[i]
            if arg == "--from-head" and i + 1 < len(argv):
                from_head_id = argv[i + 1]
                i += 2
                continue
            if arg == "--to-head" and i + 1 < len(argv):
                to_head_id = argv[i + 1]
                i += 2
                continue
            if arg == "--reason" and i + 1 < len(argv):
                reason = argv[i + 1]
                i += 2
                continue
            raise SystemExit(SURFACE_REBIND_USAGE)
        if not from_head_id or not to_head_id or not reason:
            raise SystemExit(SURFACE_REBIND_USAGE)
        return "rebind", (surface_id, from_head_id, to_head_id), reason
    raise SystemExit(f"unknown surface command: {sub}")


def parse_watch_options(argv: list[str]) -> tuple[int, bool]:
    offset = 0
    follow = False
    i = 2
    while i < len(argv):
        if argv[i] == "--offset":
            if i + 1 >= len(argv):
                raise SystemExit("usage: toas watch <run_id> [--offset <n>] [--follow]")
            try:
                offset = int(argv[i + 1])
            except ValueError as exc:
                raise SystemExit("--offset requires an integer") from exc
            i += 2
        elif argv[i] == "--follow":
            follow = True
            i += 1
        else:
            raise SystemExit(f"unknown option: {argv[i]}")
    return offset, follow


def parse_prompt_options(argv: list[str]) -> tuple[str, list[str] | None]:
    mode = "direct"
    constraints: list[str] = []
    i = 2
    while i < len(argv):
        token = argv[i]
        if token == "--mode":
            if i + 1 >= len(argv):
                raise SystemExit("usage: toas prompt <ref> [--mode <direct|mimic>] [--constraint <name> ...]")
            mode = argv[i + 1]
            i += 2
            continue
        if token == "--constraint":
            if i + 1 >= len(argv):
                raise SystemExit("usage: toas prompt <ref> [--mode <direct|mimic>] [--constraint <name> ...]")
            constraints.append(argv[i + 1])
            i += 2
            continue
        raise SystemExit(f"unknown option: {token}")
    return mode, constraints or None


def parse_graph_options(argv: list[str]) -> str:
    projection = "temporal"
    i = 1
    while i < len(argv):
        if argv[i] == "--projection":
            if i + 1 >= len(argv):
                raise SystemExit(GRAPH_USAGE)
            projection = argv[i + 1]
            i += 2
            continue
        raise SystemExit(f"unknown option: {argv[i]}")
    if projection not in {"temporal", "consequence"}:
        raise SystemExit(GRAPH_USAGE)
    return projection


def parse_ancestry_options(argv: list[str]) -> tuple[int | None, bool]:
    depth: int | None = None
    full = False
    i = 2
    while i < len(argv):
        if argv[i] == "--depth":
            if i + 1 >= len(argv):
                raise SystemExit("usage: toas ancestry <message_id> [--depth <n>] [--full]")
            try:
                depth = int(argv[i + 1])
            except ValueError as exc:
                raise SystemExit("--depth requires an integer") from exc
            i += 2
        elif argv[i] == "--full":
            full = True
            i += 1
        else:
            raise SystemExit(f"unknown option: {argv[i]}")
    return depth, full
