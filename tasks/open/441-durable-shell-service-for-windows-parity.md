# 441: Durable Shell Service for Windows Parity

## Problem
Current shell execution on Windows uses a per-command `bash -lc` launcher to ensure MSYS2 path resolution and profile loading. This introduces significant overhead and produces `Inappropriate ioctl for device` noise because Bash cannot initialize job control without a TTY.

## Goal
Implement a persistent `ShellService` within the TOAS daemon that maintains a long-lived Bash process, reducing execution latency and eliminating initialization noise.

## Proposed Approach
- **Persistence:** Maintain a single `subprocess.Popen` instance with pipes for `stdin`, `stdout`, and `stderr`.
- **Isolation:** Tie the shell lifecycle to the session or workspace.
- **Synchronization:** Use unique sentinels/delimiters written to `stdin` to mark the start and end of command output for reliable capturing.
- **PTY (Optional/Future):** Explore `conpty` or `pyte` to provide a real pseudo-terminal, which would natively solve the `ioctl` issue and allow TTY-aware tools.
- **State:** Decided whether `cd` and `export` should persist across steps (matching a real terminal) or be reset.

## Success Criteria
- `shell` and `shell_script` operations exhibit significantly lower latency on Windows.
- "Inappropriate ioctl for device" and "no job control" errors are eliminated from `stderr`.
- Environment variables (like `$OneDrive`) and pathing remain correct.