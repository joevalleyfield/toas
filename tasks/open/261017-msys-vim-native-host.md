# MSYS Vim and Native Python Host Interoperability

Filed as: 261017-msys-vim-native-host
FKA:
AKA: Git Bash Vim; mixed Vim host runtimes; MSYS temporary paths
Legacy index:

keywords: tooling, hardening, compatibility, windows, vim, msys

Parent: `261015-windows-compatibility-restoration`
Related: `261017-vim-harness-windows`

Status: OPEN; classify the mixed-runtime contract separately from native Vim

Git Bash selects its MSYS Vim, while PowerShell selects native Windows Vim via
vim.bat on this machine. Windows Python uses ConPTY for both; that does not make
their paths, job launchers, shell commands, or exit hooks equivalent.

Slash-separated driver paths restore the MSYS baseline. A bounded direct
real-host probe still times out after an exit-hook E282: Cannot read from an
MSYS /tmp/v... temporary file, through toas_host_stop_on_exit and
toas_system_in_workdir. A broad exploratory mixed-runtime run was stopped after
the outer pytest timeout; it provides no complete aggregate or success claim.

The native contract passes. TOAS_TEST_VIM_BIN allows the pytest wrappers to select
native Windows Vim explicitly from Git Bash; explicit driver executable paths
take precedence over that override.

Next: establish supported MSYS/native-host behavior, reproduce shell/temp-path
and workdir translation boundaries, and verify real host startup, transcript
rendering, and cleanup without changing the native or POSIX contracts.
