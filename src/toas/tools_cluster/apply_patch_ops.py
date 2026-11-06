from __future__ import annotations

import importlib
from difflib import SequenceMatcher, unified_diff

from .file_write_edges import write_text_with_tool_newline_policy


class ApplyPatchExecutionError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        applied_hunks: list[dict] | None = None,
        failed_hunk: dict | None = None,
        skipped_hunks: list[dict] | None = None,
        files_touched: list[str] | None = None,
        unapplied_patch: str | None = None,
    ) -> None:
        super().__init__(message)
        self.applied_hunks = applied_hunks if applied_hunks is not None else []
        self.failed_hunk = failed_hunk
        self.skipped_hunks = skipped_hunks if skipped_hunks is not None else []
        self.files_touched = files_touched if files_touched is not None else []
        self.unapplied_patch = unapplied_patch


def render_apply_patch_hunks(hunks: list[dict]) -> str:
    lines = ["*** Begin Patch"]
    for hunk in hunks:
        kind = hunk.get("kind")
        path = hunk.get("path", "")
        if kind == "add":
            lines.append(f"*** Add File: {path}")
            for add_line in hunk.get("lines", []):
                lines.append(f"+{add_line}")
        elif kind == "delete":
            lines.append(f"*** Delete File: {path}")
        elif kind == "update":
            lines.append(f"*** Update File: {path}")
            move_to = hunk.get("move_to")
            if move_to:
                lines.append(f"*** Move to: {move_to}")
            for chunk in hunk.get("change_chunks", []):
                lines.append("@@")
                lines.extend(chunk)
        else:
            raise RuntimeError(f"invalid apply_patch hunk kind: {kind}")
    lines.append("*** End Patch")
    return "\n".join(lines) + "\n"


def _normalize_add_lines(lines: list[str]) -> list[str]:
    if not lines or any(line.startswith("+") for line in lines if line):
        return lines
    non_empty = [line for line in lines if line.strip()]
    if not non_empty:
        return lines
    first = non_empty[0]
    first_indent = len(first) - len(first.lstrip(" "))
    if first_indent > 0:
        for k in range(1, first_indent + 1):
            if all(len(line) > k and line[:k] == " " * k and line[k] == "+" for line in non_empty):
                return [line[k:] if len(line) >= k else "" for line in lines]
    return lines


def _normalize_chunk_diff_lines(lines: list[str]) -> list[str]:
    if not lines or any(line and line[0] in {"+", "-"} for line in lines):
        return lines
    non_empty = [line for line in lines if line.strip()]
    if not non_empty:
        return lines

    first = non_empty[0]
    first_indent = len(first) - len(first.lstrip(" "))
    if first_indent > 0:
        for k in range(1, first_indent + 1):
            if all(len(line) > k and line[:k] == " " * k and line[k] in {" ", "+", "-"} for line in non_empty):
                if any(line[k] in {"+", "-"} for line in non_empty):
                    return [line[k:] if len(line) >= k else "" for line in lines]
    return lines


def parse_apply_patch_hunks(patch: str) -> list[dict]:
    raw_lines = patch.splitlines()
    while raw_lines and not raw_lines[0].strip():
        raw_lines.pop(0)
    while raw_lines and not raw_lines[-1].strip():
        raw_lines.pop()

    if not raw_lines or raw_lines[0].lstrip() != "*** Begin Patch":
        raise RuntimeError("invalid arguments for tool apply_patch: patch must start with '*** Begin Patch'")
    if raw_lines[-1].lstrip() != "*** End Patch":
        raise RuntimeError("invalid arguments for tool apply_patch: patch must end with '*** End Patch'")

    non_blank = [l for l in raw_lines if l.strip()]
    common_indent = len(non_blank[0]) - len(non_blank[0].lstrip(" "))
    for l in non_blank[1:]:
        indent = len(l) - len(l.lstrip(" "))
        if indent < common_indent:
            common_indent = indent
    if common_indent > 0:
        lines = [l[common_indent:] if len(l) >= common_indent else "" for l in raw_lines]
    else:
        lines = raw_lines

    hunks: list[dict] = []
    i = 1
    end = len(lines) - 1
    while i < end:
        line = lines[i]
        line_lstrip = line.lstrip()
        if line_lstrip.startswith("*** Add File: "):
            filename = line_lstrip[len("*** Add File: ") :].strip()
            i += 1
            add_lines_raw: list[str] = []
            while i < end and not lines[i].lstrip().startswith("*** "):
                add_lines_raw.append(lines[i])
                i += 1
            add_lines_norm = _normalize_add_lines(add_lines_raw)
            add_lines: list[str] = []
            for cur in add_lines_norm:
                if not cur.startswith("+"):
                    raise RuntimeError("invalid apply_patch add hunk: expected '+' lines only")
                add_lines.append(cur[1:])
            hunks.append({"kind": "add", "path": filename, "lines": add_lines})
            continue
        if line_lstrip.startswith("*** Delete File: "):
            filename = line_lstrip[len("*** Delete File: ") :].strip()
            hunks.append({"kind": "delete", "path": filename})
            i += 1
            continue
        if line_lstrip.startswith("*** Update File: "):
            filename = line_lstrip[len("*** Update File: ") :].strip()
            i += 1
            move_to: str | None = None
            if i < end and lines[i].lstrip().startswith("*** Move to: "):
                move_to = lines[i].lstrip()[len("*** Move to: ") :].strip()
                i += 1
            change_chunks: list[list[str]] = []
            current_chunk_raw: list[str] = []
            while i < end and not lines[i].lstrip().startswith("*** "):
                cur = lines[i]
                if cur.lstrip().startswith("@@"):
                    if current_chunk_raw:
                        norm_chunk = _normalize_chunk_diff_lines(current_chunk_raw)
                        for cl in norm_chunk:
                            if cl and cl[0] not in {" ", "+", "-"}:
                                raise RuntimeError("invalid apply_patch update hunk: expected context/add/remove lines")
                        change_chunks.append(norm_chunk)
                        current_chunk_raw = []
                    i += 1
                    continue
                current_chunk_raw.append(cur)
                i += 1
            if current_chunk_raw:
                norm_chunk = _normalize_chunk_diff_lines(current_chunk_raw)
                for cl in norm_chunk:
                    if cl and cl[0] not in {" ", "+", "-"}:
                        raise RuntimeError("invalid apply_patch update hunk: expected context/add/remove lines")
                change_chunks.append(norm_chunk)
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


def find_unique_stripped_match(
    original_lines: list[str], change_lines: list[str]
) -> tuple[int, list[str], list[str]] | None:
    old_chunk, _ = split_old_new_chunk(change_lines)
    if not old_chunk or not any(line.strip() for line in old_chunk):
        return None

    chunk_len = len(old_chunk)
    max_start = len(original_lines) - chunk_len
    if max_start < 0:
        return None

    stripped_old = [line.strip() for line in old_chunk]
    matches: list[int] = []
    for start in range(0, max_start + 1):
        candidate = original_lines[start : start + chunk_len]
        if [line.strip() for line in candidate] == stripped_old:
            matches.append(start)

    if len(matches) != 1:
        return None

    start_idx = matches[0]
    candidate = original_lines[start_idx : start_idx + chunk_len]

    # Map context and removal lines to target candidate lines
    cand_idx = 0
    change_info: list[dict] = []
    for raw in change_lines:
        prefix = raw[0] if raw else " "
        text = raw[1:] if raw else ""
        if prefix in {" ", "-"}:
            file_line = candidate[cand_idx]
            cand_idx += 1
            f_indent = len(file_line) - len(file_line.lstrip(" "))
            h_indent = len(text) - len(text.lstrip(" "))
            change_info.append(
                {
                    "prefix": prefix,
                    "text": text,
                    "file_line": file_line,
                    "delta": f_indent - h_indent,
                    "non_empty": bool(text.strip()),
                }
            )
        else:
            change_info.append(
                {
                    "prefix": prefix,
                    "text": text,
                    "file_line": None,
                    "delta": None,
                    "non_empty": bool(text.strip()),
                }
            )

    reconciled_new: list[str] = []
    for idx, info in enumerate(change_info):
        prefix = info["prefix"]
        text = info["text"]
        if prefix == "-":
            continue
        if prefix == " ":
            reconciled_new.append(info["file_line"])
            continue
        if prefix == "+":
            if not text.strip():
                reconciled_new.append(text)
                continue
            anchor_delta = 0
            for prev_idx in range(idx - 1, -1, -1):
                if change_info[prev_idx]["prefix"] in {" ", "-"} and change_info[prev_idx]["non_empty"]:
                    anchor_delta = change_info[prev_idx]["delta"]
                    break
            else:
                for next_idx in range(idx + 1, len(change_info)):
                    if change_info[next_idx]["prefix"] in {" ", "-"} and change_info[next_idx]["non_empty"]:
                        anchor_delta = change_info[next_idx]["delta"]
                        break

            added_indent = len(text) - len(text.lstrip(" "))
            new_indent = max(0, added_indent + anchor_delta)
            reconciled_new.append(" " * new_indent + text.lstrip(" "))

    return start_idx, candidate, reconciled_new


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
            stripped = find_unique_stripped_match(original_lines, change_lines)
            if stripped is not None:
                start, old_chunk, new_chunk = stripped
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
    config = tools_mod._workspace_config()
    newline_style_policy = config.tool_writes.newline_style

    if "atomic" in args:
        raw_atomic = args["atomic"]
        if isinstance(raw_atomic, str):
            atomic = raw_atomic.lower() not in {"false", "0", "no"}
        else:
            atomic = bool(raw_atomic)
    else:
        atomic = getattr(config.tool_writes, "patch_atomic", True)

    hunks = parse_apply_patch_hunks(patch)
    total_hunks = len(hunks)

    if atomic:
        file_state: dict = {}
        touched: list[str] = []

        def get_file_content(p) -> str | None:
            if p in file_state:
                return file_state[p]
            if p.is_file():
                content = p.read_text(encoding="utf-8")
                file_state[p] = content
                return content
            return None

        def path_exists(p) -> bool:
            if p in file_state:
                return file_state[p] is not None
            return p.exists()

        planned_actions: list[dict] = []
        for k, hunk in enumerate(hunks):
            kind = hunk["kind"]
            path_arg = hunk.get("path")
            if not isinstance(path_arg, str) or not path_arg:
                raise ApplyPatchExecutionError(
                    f"tool apply_patch failed at hunk {k + 1}/{total_hunks}: invalid apply_patch hunk: missing file path",
                    failed_hunk={"index": k + 1, "path": path_arg or "", "error": "missing file path"},
                    skipped_hunks=[
                        {"index": j + 1, "path": hunks[j].get("path", "")} for j in range(k + 1, total_hunks)
                    ],
                    unapplied_patch=patch,
                )

            path = workspace_path_fn(path_arg)
            try:
                if kind == "add":
                    if path_exists(path):
                        raise RuntimeError(f"tool apply_patch add failed: file already exists: {path_arg}")
                    content = "\n".join(hunk["lines"])
                    if hunk["lines"] and not content.endswith("\n"):
                        content += "\n"
                    file_state[path] = content
                    planned_actions.append({"type": "write", "path": path, "content": content})
                    touched.append(path_arg)
                    continue

                if kind == "delete":
                    if not path_exists(path):
                        raise RuntimeError(f"tool apply_patch delete failed: file does not exist: {path_arg}")
                    if path.is_dir() and path not in file_state:
                        raise RuntimeError(f"tool apply_patch delete failed: path is a directory: {path_arg}")
                    file_state[path] = None
                    planned_actions.append({"type": "delete", "path": path})
                    touched.append(path_arg)
                    continue

                if kind == "update":
                    content_maybe = get_file_content(path)
                    if content_maybe is None:
                        raise RuntimeError(f"tool apply_patch update failed: file does not exist: {path_arg}")
                    content = content_maybe
                    original_lines = content.splitlines()
                    updated_lines = apply_update_change_chunks(original_lines, hunk["change_chunks"], path_arg)
                    updated = "\n".join(updated_lines)
                    if content.endswith("\n"):
                        updated += "\n"
                    file_state[path] = updated

                    move_to = hunk.get("move_to")
                    if isinstance(move_to, str) and move_to:
                        target = workspace_path_fn(move_to)
                        if path_exists(target):
                            raise RuntimeError(f"tool apply_patch move failed: target exists: {move_to}")
                        file_state[target] = updated
                        file_state[path] = None
                        planned_actions.append({"type": "delete", "path": path})
                        planned_actions.append({"type": "write", "path": target, "content": updated})
                        touched.append(path_arg)
                        touched.append(move_to)
                    else:
                        planned_actions.append({"type": "write", "path": path, "content": updated})
                        touched.append(path_arg)
                    continue

                raise RuntimeError(f"invalid apply_patch hunk kind: {kind}")
            except Exception as err:
                raise ApplyPatchExecutionError(
                    f"tool apply_patch failed at hunk {k + 1}/{total_hunks} ({path_arg}): {err}",
                    failed_hunk={"index": k + 1, "path": path_arg, "error": str(err)},
                    skipped_hunks=[
                        {"index": j + 1, "path": hunks[j].get("path", "")} for j in range(k + 1, total_hunks)
                    ],
                    unapplied_patch=patch,
                ) from None

        for action in planned_actions:
            atype = action["type"]
            if atype == "delete":
                p = action["path"]
                if p.exists():
                    p.unlink()
            elif atype == "write":
                p = action["path"]
                p.parent.mkdir(parents=True, exist_ok=True)
                write_text_with_tool_newline_policy(
                    path=p,
                    text=action["content"],
                    newline_style_policy=newline_style_policy,
                )

        unique_touched = list(dict.fromkeys(touched))
        return {
            "tool_name": "apply_patch",
            "ok": True,
            "summary": f"applied {len(hunks)} hunk(s) across {len(unique_touched)} file(s)",
            "hunks_applied": len(hunks),
            "files_touched": unique_touched,
            "atomic": True,
        }

    # Non-atomic mode
    touched = []
    applied_hunks: list[dict] = []
    for k, hunk in enumerate(hunks):
        kind = hunk["kind"]
        path_arg = hunk.get("path")
        if not isinstance(path_arg, str) or not path_arg:
            raise ApplyPatchExecutionError(
                f"tool apply_patch non-atomic failed at hunk {k + 1}/{total_hunks}: invalid apply_patch hunk: missing file path",
                applied_hunks=applied_hunks,
                failed_hunk={"index": k + 1, "path": path_arg or "", "error": "missing file path"},
                skipped_hunks=[
                    {"index": j + 1, "path": hunks[j].get("path", "")} for j in range(k + 1, total_hunks)
                ],
                files_touched=list(dict.fromkeys(touched)),
                unapplied_patch=render_apply_patch_hunks(hunks[k:]),
            )

        path = workspace_path_fn(path_arg)
        try:
            if kind == "add":
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
                applied_hunks.append(hunk)
                continue

            if kind == "delete":
                if not path.exists():
                    raise RuntimeError(f"tool apply_patch delete failed: file does not exist: {path_arg}")
                if path.is_dir():
                    raise RuntimeError(f"tool apply_patch delete failed: path is a directory: {path_arg}")
                path.unlink()
                touched.append(path_arg)
                applied_hunks.append(hunk)
                continue

            if kind == "update":
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
                applied_hunks.append(hunk)
                continue

            raise RuntimeError(f"invalid apply_patch hunk kind: {kind}")
        except Exception as err:
            unique_touched = list(dict.fromkeys(touched))
            skipped = [{"index": j + 1, "path": hunks[j].get("path", "")} for j in range(k + 1, total_hunks)]
            applied_summary = (
                f"{len(applied_hunks)} hunk(s) applied ({', '.join(unique_touched) if unique_touched else 'none'})"
            )
            skipped_summary = f"{len(skipped)} hunk(s) skipped"
            raise ApplyPatchExecutionError(
                f"tool apply_patch non-atomic execution failed at hunk {k + 1}/{total_hunks} ({path_arg}): {err}\n"
                f"{applied_summary}; {skipped_summary}.",
                applied_hunks=applied_hunks,
                failed_hunk={"index": k + 1, "path": path_arg, "error": str(err)},
                skipped_hunks=skipped,
                files_touched=unique_touched,
                unapplied_patch=render_apply_patch_hunks(hunks[k:]),
            ) from None

    unique_touched = list(dict.fromkeys(touched))
    return {
        "tool_name": "apply_patch",
        "ok": True,
        "summary": f"applied {len(hunks)} hunk(s) across {len(unique_touched)} file(s)",
        "hunks_applied": len(hunks),
        "files_touched": unique_touched,
        "atomic": False,
    }
