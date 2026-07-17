# Shell-Attached Stdio Host Spike

This spike tests whether an interactive zsh can keep a private TOAS host warm
over retained stdio pipes. It is deliberately not a supported CLI surface.

Load the hook from the repository root:

```zsh
eval "$(spikes/shell_host_stdio/shell-init.zsh --emit)"
```

The first request lazily starts the host; the second reuses it:

```zsh
toas_shell_spike status
toas_shell_spike status
```

An interrupt probe demonstrates that a foreground client can send a cancel
request over the same full-duplex channel:

```zsh
toas_shell_spike cancel-probe
# Press Ctrl-C.
```

The probe intentionally uses a missing run id, so the expected response is an
`op_error`; the evidence being tested is that SIGINT reaches the foreground
client and that the client can write and receive a second protocol exchange on
the retained host pipes.

Use `toas_shell_spike_stop` for explicit cleanup. Otherwise the host watches the
owner shell PID and exits after the shell exits.

## Boundaries and findings

- The existing newline-delimited JSON protocol works unchanged.
- The host's existing `--owner-pid` watchdog supplies the desired shell-bound
  lifetime.
- A short-lived client can inherit duplicated pipe descriptors while ordinary
  stdin/stdout remain attached to the terminal.
- The host's stderr must also be redirected deliberately. Letting it inherit a
  caller's terminal or capture pipe can keep that outer pipe alive after the
  shell itself exits.
- This spike assumes one foreground client at a time. Concurrent/background
  clients would need a shell-local multiplexer or lock.
- zsh has one ambient coprocess slot. Starting this host with `coproc` can
  conflict with an unrelated coprocess owned by the user's shell. A production
  hook should avoid claiming that singleton blindly, likely by using an
  explicit pipe-launch helper that returns dedicated descriptors.
- The Python FD client still pays interpreter startup. The retained host proves
  runtime warmth; a tiny client shim can be considered separately if client
  startup remains material.
