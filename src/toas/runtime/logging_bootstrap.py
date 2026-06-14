import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..config import DiagnosticsPolicy


def configure_logging(policy: "DiagnosticsPolicy") -> None:
    level = getattr(logging, policy.log_level.upper(), logging.WARNING)
    handlers: list[logging.Handler] = []
    if policy.log_file:
        handler: logging.Handler = logging.FileHandler(policy.log_file, encoding="utf-8")
    else:
        handler = logging.StreamHandler()
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    handlers.append(handler)
    logging.basicConfig(level=level, handlers=handlers, force=True)
