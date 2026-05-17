import pytest


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        path = str(item.fspath).replace("\\", "/")
        if "/tests/acceptance/" in path:
            item.add_marker(pytest.mark.acceptance)
