#!/usr/bin/env python3
"""
jj_scratch.py - Manage Jujutsu scratch workspaces in conversation scratch space.

Provides zero-collision, isolated working copies attached to the parent jj repo.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys


def run_cmd(cmd: list[str], cwd: str | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if check and res.returncode != 0:
        err = res.stderr.strip() or res.stdout.strip()
        raise RuntimeError(f"Command failed ({' '.join(cmd)}): {err}")
    return res


def get_repo_root() -> str:
    res = run_cmd(["jj", "root"], check=False)
    if res.returncode != 0:
        print("Error: Not in a Jujutsu repository (jj root failed).", file=sys.stderr)
        sys.exit(1)
    return res.stdout.strip()


def find_default_scratch_base() -> str:
    """Locate the best conversation scratch directory."""
    if "ANTIGRAVITY_SCRATCH_DIR" in os.environ:
        base = os.path.join(os.environ["ANTIGRAVITY_SCRATCH_DIR"], "workspaces")
        os.makedirs(base, exist_ok=True)
        return base

    conv_id = os.environ.get("ANTIGRAVITY_CONVERSATION_ID")
    app_data = os.environ.get("ANTIGRAVITY_APP_DATA_DIR", os.path.expanduser("~/.gemini/antigravity"))
    if conv_id:
        scratch = os.path.join(app_data, "brain", conv_id, "scratch", "workspaces")
        os.makedirs(scratch, exist_ok=True)
        return scratch

    repo_name = os.path.basename(get_repo_root())
    tmp_scratch = os.path.join("/tmp", "jj-scratch", repo_name)
    os.makedirs(tmp_scratch, exist_ok=True)
    return tmp_scratch


def _parse_varint(data: bytes, offset: int) -> tuple[int, int]:
    val = 0
    shift = 0
    while offset < len(data):
        b = data[offset]
        offset += 1
        val |= (b & 0x7F) << shift
        if not (b & 0x80):
            break
        shift += 7
    return val, offset


def parse_workspace_index(repo_root: str) -> dict[str, str]:
    """Parse .jj/repo/workspace_store/index to get workspace name -> absolute directory."""
    index_path = os.path.join(repo_root, ".jj", "repo", "workspace_store", "index")
    if not os.path.isfile(index_path):
        return {}

    workspaces: dict[str, str] = {}
    with open(index_path, "rb") as f:
        data = f.read()

    repo_dir = os.path.join(repo_root, ".jj", "repo")
    offset = 0
    try:
        while offset < len(data):
            tag_wire, offset = _parse_varint(data, offset)
            field_num = tag_wire >> 3
            wire_type = tag_wire & 7
            if wire_type == 2:  # length-delimited
                length, offset = _parse_varint(data, offset)
                sub_data = data[offset : offset + length]
                offset += length
                if field_num == 1:  # workspace entry
                    sub_off = 0
                    name = None
                    path = None
                    while sub_off < len(sub_data):
                        stag, sub_off = _parse_varint(sub_data, sub_off)
                        snum = stag >> 3
                        swire = stag & 7
                        if swire == 2:
                            slen, sub_off = _parse_varint(sub_data, sub_off)
                            val = sub_data[sub_off : sub_off + slen].decode("utf-8", errors="ignore")
                            sub_off += slen
                            if snum == 1:
                                name = val
                            elif snum == 2:
                                path = val
                        elif swire == 0:
                            _, sub_off = _parse_varint(sub_data, sub_off)
                        else:
                            break
                    if name and path:
                        workspaces[name] = os.path.abspath(os.path.join(repo_dir, path))
            elif wire_type == 0:
                _, offset = _parse_varint(data, offset)
            else:
                break
    except Exception:
        pass

    return workspaces


def cmd_create(args: argparse.Namespace) -> None:
    repo_root = get_repo_root()
    name = args.name
    rev = args.rev or "@-"

    existing = parse_workspace_index(repo_root)
    if name in existing:
        print(f"Error: Workspace '{name}' already exists at {existing[name]}.", file=sys.stderr)
        sys.exit(1)

    if args.dir:
        target_dir = os.path.abspath(args.dir)
    else:
        base_dir = find_default_scratch_base()
        target_dir = os.path.join(base_dir, name)

    if os.path.exists(target_dir) and os.listdir(target_dir):
        print(f"Error: Target directory '{target_dir}' already exists and is not empty.", file=sys.stderr)
        sys.exit(1)

    print(f"Creating jj workspace '{name}' at:\n  {target_dir}")
    print(f"Parent revision: {rev}")

    run_cmd(["jj", "workspace", "add", target_dir, "--name", name, "-r", rev], cwd=repo_root)

    change_res = run_cmd(
        ["jj", "-R", target_dir, "log", "-r", "@", "--no-graph", "-T", 'change_id.shortest() ++ " (" ++ commit_id.shortest() ++ ")"'],
        cwd=repo_root,
        check=False,
    )
    change_info = change_res.stdout.strip() if change_res.returncode == 0 else "unknown"

    print("\nWorkspace ready!")
    print(f"  Working copy commit: {name}@ ({change_info})")
    print(f"  Path: {target_dir}")


def cmd_list(args: argparse.Namespace) -> None:
    repo_root = get_repo_root()
    ws_paths = parse_workspace_index(repo_root)
    raw_list = run_cmd(["jj", "workspace", "list"], cwd=repo_root).stdout.strip().splitlines()

    print(f"Jujutsu workspaces for repo: {repo_root}\n")
    print(f"{'NAME':<20} {'EXISTS':<8} {'PATH':<50}")
    print(f"{'-'*18} {'-'*6} {'-'*48}")

    for line in raw_list:
        if ":" not in line:
            continue
        ws_name = line.split(":", 1)[0].strip()
        path = ws_paths.get(ws_name, "(path unknown)")
        exists = "yes" if os.path.isdir(path) else "MISSING"
        print(f"{ws_name:<20} {exists:<8} {path:<50}")


def cmd_forget(args: argparse.Namespace) -> None:
    repo_root = get_repo_root()
    name = args.name
    ws_paths = parse_workspace_index(repo_root)
    path = ws_paths.get(name)

    print(f"Forgetting workspace '{name}'...")
    run_cmd(["jj", "workspace", "forget", name], cwd=repo_root)

    if args.delete and path and os.path.isdir(path):
        print(f"Removing directory: {path}")
        shutil.rmtree(path, ignore_errors=True)

    print(f"Workspace '{name}' forgotten successfully.")


def cmd_prune(args: argparse.Namespace) -> None:
    repo_root = get_repo_root()
    ws_paths = parse_workspace_index(repo_root)
    pruned = 0

    print("Checking for orphaned/missing workspaces...")
    for name, path in ws_paths.items():
        if name == "default":
            continue
        if not os.path.isdir(path):
            print(f"  Orphaned: '{name}' -> {path} does not exist.")
            if not args.dry_run:
                run_cmd(["jj", "workspace", "forget", name], cwd=repo_root)
                print(f"    Forgot '{name}'.")
            pruned += 1

    if pruned == 0:
        print("No orphaned workspaces found.")
    else:
        action = "Found" if args.dry_run else "Pruned"
        print(f"\n{action} {pruned} orphaned workspace(s).")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Manage Jujutsu scratch workspaces in conversation scratch space."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_create = subparsers.add_parser("create", help="Create a new scratch workspace")
    p_create.add_argument("name", help="Name for the new workspace")
    p_create.add_argument("-r", "--rev", help="Parent revision (default: @-)")
    p_create.add_argument("-d", "--dir", help="Explicit target directory")
    p_create.set_defaults(func=cmd_create)

    p_list = subparsers.add_parser("list", help="List registered workspaces")
    p_list.set_defaults(func=cmd_list)

    p_forget = subparsers.add_parser("forget", help="Forget a workspace and optionally delete directory")
    p_forget.add_argument("name", help="Workspace name to forget")
    p_forget.add_argument("--delete", action="store_true", help="Delete directory")
    p_forget.set_defaults(func=cmd_forget)

    p_prune = subparsers.add_parser("prune", help="Prune missing workspaces")
    p_prune.add_argument("--dry-run", action="store_true", help="Dry run prune")
    p_prune.set_defaults(func=cmd_prune)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
