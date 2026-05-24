import os
from pathlib import Path

from ..config import OperatorConfig, apply_overrides, config_from_discovered_paths
from ..graph import active_config_overrides, read_log


def load_operator_config_for_workdir(workdir: str | Path) -> OperatorConfig:
    wd = Path(workdir).resolve()
    file_config = config_from_discovered_paths(workdir=wd)
    events_path = wd / ".toas" / "events.jsonl"
    events = read_log(str(events_path)) if events_path.exists() else []
    session_overrides = active_config_overrides(events)
    return apply_overrides(file_config, session_overrides)


def stream_flags_for_workdir(workdir: str | Path) -> tuple[bool, bool]:
    env_thinking = os.getenv("TOAS_STREAM_THINKING", "").strip().lower()
    env_progress = os.getenv("TOAS_STREAM_PROMPT_PROGRESS", "").strip().lower()
    env_truthy = {"1", "true", "yes", "on"}
    env_falsy = {"0", "false", "no", "off"}
    try:
        operator_config = load_operator_config_for_workdir(workdir)
    except Exception:
        thinking_flag = False
        progress_flag = False
    else:
        thinking_flag = operator_config.runtime.thinking_stream_mode == "enabled"
        progress_flag = operator_config.runtime.prompt_progress_mode == "enabled"

    if env_thinking in env_truthy:
        thinking_flag = True
    elif env_thinking in env_falsy:
        thinking_flag = False

    if env_progress in env_truthy:
        progress_flag = True
    elif env_progress in env_falsy:
        progress_flag = False

    return (
        thinking_flag,
        progress_flag,
    )
