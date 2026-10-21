# MSYS Vim and Native Python Host Interoperability

Filed as: 261017-msys-vim-native-host
FKA:
AKA: Git Bash Vim; mixed Vim host runtimes; MSYS temporary paths
Legacy index:

keywords: tooling, hardening, compatibility, windows, vim, msys

Parent: `261015-windows-compatibility-restoration`
Related: `261017-vim-harness-windows`

Status: OPEN; reconcile historical harness failure with working operator MSYS Vim

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

## Operator evidence — 2026-10-20

The operator reports that MSYS Vim works in their own use. The earlier E282
probe remains historical harness evidence, not proof that current MSYS Vim
usage is broken. Before changing code, reproduce that exact probe on the
current revision and compare its launcher/temp-path setup with the working
operator setup. Windows gVim previously failed for the operator but has not
been retried since the latest fixes; its current behavior is unverified.
Keep gVim and MSYS Vim evidence separate.
