#!/usr/bin/env zsh

# Emit a source command so the spike can be loaded with:
#   eval "$(spikes/shell_host_stdio/shell-init.zsh --emit)"
if [[ "${1:-}" == "--emit" ]]; then
  _toas_shell_hook_path="${${(%):-%x}:A}"
  print -r -- "source ${(q)_toas_shell_hook_path}"
  exit 0
fi

typeset -g _TOAS_SHELL_SPIKE_HOOK_PATH="${${(%):-%x}:A}"
typeset -g _TOAS_SHELL_SPIKE_ROOT="${_TOAS_SHELL_SPIKE_HOOK_PATH:h:h:h}"
typeset -g TOAS_SHELL_HOST_PID=""
typeset -g TOAS_SHELL_HOST_READ_FD=""
typeset -g TOAS_SHELL_HOST_WRITE_FD=""

_toas_shell_host_alive() {
  [[ -n "$TOAS_SHELL_HOST_PID" ]] &&
    [[ -n "$TOAS_SHELL_HOST_READ_FD" ]] &&
    [[ -n "$TOAS_SHELL_HOST_WRITE_FD" ]] &&
    kill -0 "$TOAS_SHELL_HOST_PID" 2>/dev/null
}

_toas_shell_host_start() {
  emulate -L zsh
  setopt no_bg_nice

  if _toas_shell_host_alive; then
    return 0
  fi

  local diag_log="${TOAS_SHELL_HOST_DIAG_LOG:-${TMPDIR:-/tmp}/toas-shell-host.$$.log}"
  coproc env \
    TOAS_HOST_STDIO_DIAG_LOG="$diag_log" \
    uv --project "$_TOAS_SHELL_SPIKE_ROOT" run toas host serve \
      --stdio-json --owner-pid "$$" \
      2>>"$diag_log.stderr"

  TOAS_SHELL_HOST_PID="$!"
  exec {TOAS_SHELL_HOST_READ_FD}<&p
  exec {TOAS_SHELL_HOST_WRITE_FD}>&p
}

toas_shell_spike() {
  _toas_shell_host_start || return $?

  python3 "$_TOAS_SHELL_SPIKE_HOOK_PATH:h/fd-client.py" \
    --read-fd 3 \
    --write-fd 4 \
    --host-pid "$TOAS_SHELL_HOST_PID" \
    "$@" \
    3<&$TOAS_SHELL_HOST_READ_FD \
    4>&$TOAS_SHELL_HOST_WRITE_FD
}

toas_shell_spike_stop() {
  if [[ -n "$TOAS_SHELL_HOST_READ_FD" ]]; then
    exec {TOAS_SHELL_HOST_READ_FD}<&-
  fi
  if [[ -n "$TOAS_SHELL_HOST_WRITE_FD" ]]; then
    exec {TOAS_SHELL_HOST_WRITE_FD}>&-
  fi
  if [[ -n "$TOAS_SHELL_HOST_PID" ]]; then
    kill "$TOAS_SHELL_HOST_PID" 2>/dev/null
    wait "$TOAS_SHELL_HOST_PID" 2>/dev/null
  fi
  TOAS_SHELL_HOST_PID=""
  TOAS_SHELL_HOST_READ_FD=""
  TOAS_SHELL_HOST_WRITE_FD=""
}
