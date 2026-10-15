# Vim verification drivers

Run the checked Vim contracts with `uv run pytest tests -k vim -o addopts= -q`.
The normal full suite includes them as well. Install a native Vim with timers,
jobs, and channels on PATH; each driver also accepts `--vim-bin` to select it
explicitly. Use `uv sync` to install the development dependencies.
Set `TOAS_TEST_VIM_BIN` to override the bare `vim` used by the pytest wrappers;
an explicit driver executable path takes precedence. In Git Bash, point it at
native Windows Vim when testing the native Windows Python host. An MSYS Vim
selected by PATH is a different runtime, with Unix path and job conventions;
the native Windows contract does not establish MSYS/native-host interoperability.

The checked drivers use `vim_terminal.py`: pexpect PTYs on POSIX and pywinpty
ConPTY on Windows. Windows `.bat`/`.cmd` Vim launchers run through cmd.exe.
Both paths run actual Vim, including the foreground keystrokes in the async timer
probe. Windows completion requires drained output and a real process exit;
ConPTY output handles can remain open after the child exits. A terminal deadline
kills the Windows process tree and reports the output tail and available logs.
Terminal completion is distinct from TOAS run completion, which still requires
the plugin's terminal protocol state and transcript assertions.

Real-host fixtures explicitly set `g:toas_workdir` to their temporary workspace
so ancestor `.toas` directories do not change their meaning. Fixture paths use
Vim-compatible separators; Python hosts that require this environment use
`sys.executable`. No Windows plugin contract is skipped.

The standalone `phase4` experiments remain POSIX terminal research probes; they
are not the checked Windows restoration suite and still use pexpect directly.
