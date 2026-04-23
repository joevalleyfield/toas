from __future__ import annotations


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
