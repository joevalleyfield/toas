from pathlib import Path

from ..config import OperatorConfig, apply_overrides, config_from_file
from ..graph import active_config_overrides, read_log


def load_operator_config_for_workdir(workdir: str | Path) -> OperatorConfig:
    wd = Path(workdir).resolve()
    file_config = config_from_file(wd / "toas.toml")
    events_path = wd / "events.jsonl"
    events = read_log(str(events_path)) if events_path.exists() else []
    session_overrides = active_config_overrides(events)
    return apply_overrides(file_config, session_overrides)


def stream_flags_for_workdir(workdir: str | Path) -> tuple[bool, bool]:
    try:
        operator_config = load_operator_config_for_workdir(workdir)
    except Exception:
        return False, False
    return (
        operator_config.runtime.thinking_stream_mode == "enabled",
        operator_config.runtime.prompt_progress_mode == "enabled",
    )
