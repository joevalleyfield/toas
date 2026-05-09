from __future__ import annotations

import atexit
import signal


def run_daemon(action: str, *, daemon_module, print_fn=print):
    def _safe_multiprocessing_atexit() -> None:
        try:
            import multiprocessing.util as mp_util
        except Exception:
            return

        try:
            atexit.unregister(mp_util._exit_function)
        except Exception:
            pass

        def _wrapped_exit_function() -> None:
            try:
                mp_util._exit_function()
            except KeyboardInterrupt:
                return

        atexit.register(_wrapped_exit_function)

    def _suppress_exit_sigint_noise() -> None:
        try:
            signal.signal(signal.SIGINT, signal.SIG_IGN)
        except (ValueError, OSError):
            pass

    if action == "start":
        state = daemon_module.start()
        _safe_multiprocessing_atexit()
        _suppress_exit_sigint_noise()
        print_fn(f"daemon running pid={state['pid']} endpoint={state['endpoint']}")
        return
    if action == "stop":
        state = daemon_module.stop()
        if state["running"]:
            raise SystemExit("daemon stop failed")
        _safe_multiprocessing_atexit()
        _suppress_exit_sigint_noise()
        print_fn("daemon stopped")
        return
    if action == "status":
        state = daemon_module.status()
        _safe_multiprocessing_atexit()
        _suppress_exit_sigint_noise()
        if state["running"]:
            print_fn(f"daemon running pid={state['pid']} endpoint={state['endpoint']}")
        else:
            print_fn(f"daemon stopped endpoint={state['endpoint']}")
        return
    raise SystemExit(f"unknown daemon command: {action}")
