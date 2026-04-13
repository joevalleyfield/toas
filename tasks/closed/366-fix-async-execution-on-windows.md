# 366: Fix async execution on Windows with msys-vim

- **Status**: Closed
- **Resolution**: Fixed

## Summary

The `ToasStep` async path was failing on Windows when using msys-vim, falling back to synchronous RPC or CLI execution. A multi-step debugging process identified and resolved several issues in sequence.

1.  **Transport Failure**: The initial symptom was the async transport path failing. Debugging showed an `empty or partial rpc response` error, indicating a timeout waiting for the `toasd` daemon.
2.  **Invalid Path**: Running the daemon in the foreground (`toasd serve`) revealed a `NotADirectoryError` on Windows. This was caused by msys-vim sending a POSIX-style path (`/c/Users/...`) as the `workdir`, which the Python `subprocess` module could not handle.
3.  **Daemon Patch**: The issue was resolved by patching `src/toas/daemon.py` to normalize the received `workdir` path from MSYS format to a native Windows format before calling `subprocess.Popen`.
4.  **Encoding Error**: With the transport fixed, the `toas step` subprocess began executing but failed with a `UnicodeDecodeError` when reading `session.md`.
5.  **CLI Patch**: The final issue was resolved by patching `src/toas/cli.py` to handle potential encoding errors gracefully by replacing invalid characters when opening text files.

These changes restore the intended asynchronous execution flow.
