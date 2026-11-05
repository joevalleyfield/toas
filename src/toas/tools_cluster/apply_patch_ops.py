from __future__ import annotations

import importlib
from difflib import SequenceMatcher, unified_diff

from .file_write_edges import write_text_with_tool_newline_policy


def parse_apply_patch_hunks(patch: str) -> list[dict]:
    lines = patch.splitlines()
    if not lines or lines[0] != "*** Begin Patch":
        raise RuntimeError("invalid arguments for tool apply_patch: patch must start with '*** Begin Patch'")
    if lines[-1] != "*** End Patch":
        raise RuntimeError("invalid arguments for tool apply_patch: patch must end with '*** End Patch'")

    hunks: list[dict] = []
    i = 1
    end = len(lines) - 1
    while i < end:
        line = lines[i]
        if line.startswith("*** Add File: "):
            filename = line[len("*** Add File: ") :]
            i += 1
            add_lines: list[str] = []
            while i < end and not lines[i].startswith("*** "):
                cur = lines[i]
                if not cur.startswith("+"):
                    raise RuntimeError("invalid apply_patch add hunk: expected '+' lines only")
                add_lines.append(cur[1:])
                i += 1
            hunks.append({"kind": "add", "path": filename, "lines": add_lines})
            continue
        if line.startswith("*** Delete File: "):
            filename = line[len("*** Delete File: ") :]
            hunks.append({"kind": "delete", "path": filename})
            i += 1
            continue
        if line.startswith("*** Update File: "):
            filename = line[len("*** Update File: ") :]
            i += 1
            move_to: str | None = None
            if i < end and lines[i].startswith("*** Move to: "):
                move_to = lines[i][len("*** Move to: ") :]
                i += 1
            change_chunks: list[list[str]] = []
            current_chunk: list[str] = []
            while i < end and not lines[i].startswith("*** "):
                cur = lines[i]
                if cur.startswith("@@"):
                    if current_chunk:
                        change_chunks.append(current_chunk)
                        current_chunk = []
                    i += 1
                    continue
                if cur and cur[0] not in {" ", "+", "-"}:
                    raise RuntimeError("invalid apply_patch update hunk: expected context/add/remove lines")
                current_chunk.append(cur)
                i += 1
            if current_chunk:
                change_chunks.append(current_chunk)
            hunks.append({"kind": "update", "path": filename, "move_to": move_to, "change_chunks": change_chunks})
            continue
        raise RuntimeError(f"invalid apply_patch hunk header: {line}")

    if not hunks:
        raise RuntimeError("invalid arguments for tool apply_patch: patch must include at least one hunk")
    return hunks


def find_chunk_start(lines: list[str], chunk: list[str], start_at: int) -> int:
    if not chunk:
        return start_at
    max_start = len(lines) - len(chunk)
    for idx in range(max(start_at, 0), max_start + 1):
        if lines[idx : idx + len(chunk)] == chunk:
            return idx
    return -1


def _shift_indent(lines: list[str], delta: int) -> list[str]:
    shifted: list[str] = []
    for line in lines:
        if not line.strip():
            shifted.append(line)
        elif delta > 0:
            shifted.append(" " * delta + line)
        else:
            to_remove = -delta
            leading = len(line) - len(line.lstrip(" "))
            remove_count = min(to_remove, leading)
            shifted.append(line[remove_count:])
    return shifted


def find_unique_indent_shifted_chunk(
    lines: list[str], old_chunk: list[str], new_chunk: list[str]
) -> tuple[int, list[str], list[str]] | None:
    if not old_chunk:
        return None
    non_empty_indices = [idx for idx, line in enumerate(old_chunk) if line.strip()]
    if not non_empty_indices:
        return None

    chunk_len = len(old_chunk)
    max_start = len(lines) - chunk_len
    matches: list[tuple[int, int]] = []

    for start in range(0, max_start + 1):
        candidate = lines[start : start + chunk_len]
        # Verify non-blank stripped line parity
        mismatch = False
        deltas: list[int] = []
        for idx in range(chunk_len):
            c_line = candidate[idx]
            o_line = old_chunk[idx]
            if not o_line.strip():
                if c_line.strip():
                    mismatch = True
                    break
                continue
            if c_line.strip() != o_line.strip():
                mismatch = True
                break
            c_indent = len(c_line) - len(c_line.lstrip(" "))
            o_indent = len(o_line) - len(o_line.lstrip(" "))
            deltas.append(c_indent - o_indent)

        if not mismatch and deltas and all(d == deltas[0] for d in deltas):
            matches.append((start, deltas[0]))

    if len(matches) == 1:
        start_idx, delta = matches[0]
        shifted_old = _shift_indent(old_chunk, delta)
        shifted_new = _shift_indent(new_chunk, delta)
        return start_idx, shifted_old, shifted_new
    return None


def format_chunk_mismatch_diff(original_lines: list[str], old_chunk: list[str]) -> str:
    if not original_lines or not old_chunk:
        return ""
    chunk_len = len(old_chunk)
    if len(original_lines) <= chunk_len:
        best_window = original_lines
    else:
        best_start = 0
        best_ratio = -1.0
        search_lines = [l.strip() for l in old_chunk if l.strip()]
        candidate_starts: set[int] = {0, max(0, len(original_lines) - chunk_len)}

        for target in search_lines[:4]:
            for line_idx, file_line in enumerate(original_lines):
                if target in file_line:
                    candidate_starts.add(max(0, min(line_idx, len(original_lines) - chunk_len)))
                    candidate_starts.add(max(0, min(line_idx - chunk_len // 2, len(original_lines) - chunk_len)))

        for start in candidate_starts:
            window = original_lines[start : start + chunk_len]
            ratio = SequenceMatcher(None, [l.strip() for l in old_chunk], [l.strip() for l in window]).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_start = start

        best_window = original_lines[best_start : best_start + chunk_len]

    diff_lines = list(
        unified_diff(
            [line + "\n" for line in best_window],
            [line + "\n" for line in old_chunk],
            fromfile="actual",
            tofile="expected",
            n=2,
        )
    )
    return "".join(diff_lines).strip()


def split_old_new_chunk(change_lines: list[str]) -> tuple[list[str], list[str]]:
    old_chunk: list[str] = []
    new_chunk: list[str] = []
    for raw in change_lines:
        if not raw:
            prefix = " "
            text = ""
        else:
            prefix = raw[0]
            text = raw[1:]
        if prefix in {" ", "-"}:
            old_chunk.append(text)
        if prefix in {" ", "+"}:
            new_chunk.append(text)
    return old_chunk, new_chunk


def format_change_chunk_preview(change_lines: list[str], *, max_lines: int = 4, max_width: int = 80) -> str:
    if not change_lines:
        return "<empty>"
    rendered: list[str] = []
    for raw in change_lines[:max_lines]:
        text = raw
        if len(text) > max_width:
            text = text[: max_width - 3] + "..."
        rendered.append(text)
    if len(change_lines) > max_lines:
        rendered.append("...")
    return " | ".join(rendered)


def apply_update_change_lines(original_lines: list[str], change_lines: list[str], path_arg: str) -> list[str]:
    if not change_lines:
        return list(original_lines)
    old_chunk, new_chunk = split_old_new_chunk(change_lines)
    preview = format_change_chunk_preview(change_lines)
    if not old_chunk:
        raise RuntimeError(
            "tool apply_patch failed to apply update chunk"
            f" (unsupported context-free insertion in {path_arg}; include at least one context or removal line; chunk: {preview})"
        )
    if old_chunk == new_chunk:
        return list(original_lines)

    start = find_chunk_start(original_lines, old_chunk, 0)
    if start < 0:
        shifted = find_unique_indent_shifted_chunk(original_lines, old_chunk, new_chunk)
        if shifted is not None:
            start, old_chunk, new_chunk = shifted
        else:
            diff_text = format_chunk_mismatch_diff(original_lines, old_chunk)
            diff_msg = f"\n{diff_text}" if diff_text else ""
            raise RuntimeError(
                "tool apply_patch failed to apply update chunk"
                f" (context mismatch in {path_arg}; expected chunk not found; chunk: {preview}){diff_msg}"
            )

    end = start + len(old_chunk)
    return original_lines[:start] + new_chunk + original_lines[end:]


def apply_update_change_chunks(original_lines: list[str], change_chunks: list[list[str]], path_arg: str) -> list[str]:
    updated_lines = list(original_lines)
    for change_lines in change_chunks:
        updated_lines = apply_update_change_lines(updated_lines, change_lines, path_arg)
    return updated_lines


def run_apply_patch(args: dict, *, workspace_path_fn) -> dict:
    patch = args.get("patch")
    if not isinstance(patch, str) or not patch.strip():
        raise RuntimeError("invalid arguments for tool apply_patch: patch must be a non-empty string")

    tools_mod = importlib.import_module("toas.tools")
    newline_style_policy = tools_mod._workspace_config().tool_writes.newline_style
    hunks = parse_apply_patch_hunks(patch)
    touched: list[str] = []
    for hunk in hunks:
        kind = hunk["kind"]
        path_arg = hunk["path"]
        if not isinstance(path_arg, str) or not path_arg:
            raise RuntimeError("invalid apply_patch hunk: missing file path")

        if kind == "add":
            path = workspace_path_fn(path_arg)
            if path.exists():
                raise RuntimeError(f"tool apply_patch add failed: file already exists: {path_arg}")
            path.parent.mkdir(parents=True, exist_ok=True)
            content = "\n".join(hunk["lines"])
            if hunk["lines"] and not content.endswith("\n"):
                content += "\n"
            write_text_with_tool_newline_policy(
                path=path,
                text=content,
                newline_style_policy=newline_style_policy,
            )
            touched.append(path_arg)
            continue

        if kind == "delete":
            path = workspace_path_fn(path_arg)
            if not path.exists():
                raise RuntimeError(f"tool apply_patch delete failed: file does not exist: {path_arg}")
            if path.is_dir():
                raise RuntimeError(f"tool apply_patch delete failed: path is a directory: {path_arg}")
            path.unlink()
            touched.append(path_arg)
            continue

        if kind == "update":
            path = workspace_path_fn(path_arg)
            if not path.is_file():
                raise RuntimeError(f"tool apply_patch update failed: file does not exist: {path_arg}")
            original = path.read_text(encoding="utf-8")
            original_lines = original.splitlines()
            updated_lines = apply_update_change_chunks(original_lines, hunk["change_chunks"], path_arg)
            updated = "\n".join(updated_lines)
            if original.endswith("\n"):
                updated += "\n"
            write_text_with_tool_newline_policy(
                path=path,
                text=updated,
                newline_style_policy=newline_style_policy,
            )
            touched.append(path_arg)

            move_to = hunk.get("move_to")
            if isinstance(move_to, str) and move_to:
                target = workspace_path_fn(move_to)
                if target.exists():
                    raise RuntimeError(f"tool apply_patch move failed: target exists: {move_to}")
                target.parent.mkdir(parents=True, exist_ok=True)
                path.rename(target)
                touched.append(move_to)
            continue

        raise RuntimeError(f"invalid apply_patch hunk kind: {kind}")

    unique_touched = list(dict.fromkeys(touched))
    return {
        "tool_name": "apply_patch",
        "ok": True,
        "summary": f"applied {len(hunks)} hunk(s) across {len(unique_touched)} file(s)",
        "hunks_applied": len(hunks),
        "files_touched": unique_touched,
    }
