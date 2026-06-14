from contextlib import contextmanager

from ..runtime.local_request_ops import handle_default_op, request_workdir, run_op_capture_stdout


def run_op_capture_stdout_wrapper(*, op: str, payload: dict, cli_module, capture_stdout):
    return run_op_capture_stdout(op, payload, cli_module=cli_module, capture_stdout=capture_stdout)


@contextmanager
def request_workdir_wrapper(*, payload: dict, process_state_lock):
    with request_workdir(payload, process_state_lock=process_state_lock):
        yield


def handle_default_op_wrapper(*, payload: dict, op: str, process_state_lock, run_op_capture_stdout_fn):
    return handle_default_op(
        payload,
        op=op,
        process_state_lock=process_state_lock,
        run_op_capture_stdout_fn=run_op_capture_stdout_fn,
    )
