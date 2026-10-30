# MSYS Vim and Native Python Host Interoperability

Filed as: 261017-msys-vim-native-host
FKA:
AKA: Git Bash Vim; mixed Vim host runtimes; MSYS temporary paths
Legacy index:

keywords: tooling, hardening, closed, compatibility, windows, vim, msys

Parent: `261015-windows-compatibility-restoration`
Related: `261017-vim-harness-windows`

Status: CLOSED — 2026-10-30; supported MSYS launch passes, native-to-MSYS probe is outside scope

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

The supported launch boundary and final disposition are recorded below.

## Operator evidence — 2026-10-20

The operator reports that MSYS Vim works in their own use. The earlier E282
probe remains historical harness evidence, not proof that current MSYS Vim
usage is broken. Before changing code, reproduce that exact probe on the
current revision and compare its launcher/temp-path setup with the working
operator setup. Windows gVim previously failed for the operator but has not
been retried since the latest fixes; its current behavior is unverified.
Keep gVim and MSYS Vim evidence separate.

## Current reproduction — 2026-10-30

After fetching origin through `c9855b71` and rebasing the local documentation
commit (resulting parent `85a7b4ce`), ran the existing real-host smoke driver
on this native Windows machine with `uv` directly:

- `uv run python tests/vim/vim_plugin_real_host_smoke.py --vim-bin C:/tools/vim/vim92/gvim.exe --timeout-s 25`
  passes. Inspected its JSON artifact: nonempty run ID, `succeeded`, empty
  error, `local_host_async`, and the expected `hello from fake llm` reply in
  the rendered transcript. This verifies this gVim startup/render/exit probe,
  not every interactive gVim workflow.
- The same command selecting `C:/Program Files/Git/usr/bin/vim.exe` fails at
  the bounded 25-second deadline. Output first reports E344/E472 when Vim
  attempts to change directory to the native `C:/Users/tim/...` workspace;
  exit cleanup then reports E282 for `/tmp/v.../0` in
  `toas_host_stop_on_exit` / `toas_system_in_workdir`.

The historical MSYS harness failure is therefore current and reproducible.
Its native fixture paths and MSYS shell/temp conventions need comparison
with the operator's working launcher before attributing this to general MSYS
product failure. The gVim historical failure does not reproduce in this smoke.
No production or harness behavior was changed during this evidence pass.

## MSYS login-environment facsimile — 2026-10-30

The native-launched failure above does not reproduce the operator's normal
launch environment. A temporary adapter around the existing smoke driver
launched `C:/Program Files/Git/bin/bash.exe -lic` through ConPTY and then
`exec /usr/bin/vim`, loading Bash's interactive login startup files. The fake
model server, actual native Python host, transcript assertions, and bounded
terminal-exit check remained those of the original driver.

Three comparisons were run:

| Setup | Observed result |
| --- | --- |
| Login Bash, original fixture paths, `-Nu NONE` | Exits without the historical E282 timeout, but run fails: native Python receives `\\tmp\\toas-vim-real-host-...\\session.md` and reports file not found. Vim reports cwd under `/tmp`. |
| Login Bash, MSYS fixture paths, `-Nu NONE` | Pass: `succeeded`, expected reply rendered, real terminal exit. |
| Login Bash, MSYS fixture paths, normal Vim startup configuration | Pass with the same host/render/exit assertions. |

For the passing cases, paths used by Vim in the generated script and its
`-S`/`-V1` arguments were translated from `C:/...` to `/c/...`. The explicit
native Python host command retained its native executable and session paths.
Vim reported cwd `/c/Users/tim/AppData/Local/Temp/...`, `MSYSTEM=MINGW64`,
`shell=/usr/bin/bash`, `SHELL=/usr/bin/bash`, and `shellcmdflag=-c`.
Returned JSON artifacts were inspected: nonempty run IDs, empty errors,
`local_host_async`, and `hello from fake llm` in the transcript in both cases.

This supports the operator's report: a login-environment facsimile works;
the failing native-launched probe mixes environment and path conventions.
The comparison changes environment and fixture paths in stages, but does not
isolate which individual login variable removes E282. It also does not prove
every interactive workflow or every MSYS installation.

The exploratory adapter was removed; no checked harness or production code
changed.

## Disposition — 2026-10-30

MSYS Bash → MSYS Vim → native Windows TOAS/Python is explicitly supported
and is one of the operator's most important workflows. Preserve that support;
future changes affecting editor launch, host execution, or path handling must
verify this initialized-environment route when applicable. The support boundary
is also documented in `tests/vim/README.md`.

The operator explicitly excludes launching MSYS Vim from an uninitialized
native Windows environment from the support contract. MSYS Vim is expected
to be launched within its MSYS environment. TOAS need not detect or repair
the unsupported launch arrangement.

The supported-environment facsimile passes real native-host startup,
transcript rendering, and exit with both clean and normal Vim configuration.
This reconciles the historical harness failure with working operator use.
Closed: no product defect remains demonstrated, and adding a dedicated MSYS
harness mode is not a prerequisite for closure. Future MSYS verification
should reproduce the supported environment rather than promote the direct
native-launched probe into a compatibility requirement.
