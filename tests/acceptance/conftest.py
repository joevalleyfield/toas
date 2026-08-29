import pytest


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    args = config.invocation_params.args
    explicit_timeout = any(arg == "--timeout" or arg.startswith("--timeout=") for arg in args)
    acceptance_mode = config.getoption("--acceptance-backend-mode")
    acceptance_timeout = 5 if acceptance_mode == "replay_only" else 60
    for item in items:
        path = str(item.fspath).replace("\\", "/")
        if "/tests/acceptance/" in path:
            item.add_marker(pytest.mark.acceptance)
            if not explicit_timeout:
                item.add_marker(pytest.mark.timeout(acceptance_timeout))
