from pathlib import Path


def with_workdir(payload: dict | None, *, workdir: str | Path) -> dict:
    normalized = {} if payload is None else dict(payload)
    normalized.setdefault("workdir", str(Path(workdir).resolve()))
    return normalized


def drop_none_fields(payload: dict) -> dict:
    return {key: value for key, value in payload.items() if value is not None}
