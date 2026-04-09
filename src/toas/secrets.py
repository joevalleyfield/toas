import os


def resolve_secret(*, source: str, ref: str, default: str = "") -> str:
    source_norm = (source or "env").strip().lower()
    if source_norm == "env":
        key = ref.strip() or "TOAS_LLM_API_KEY"
        return os.environ.get(key, default)
    if source_norm == "keyring":
        target = ref.strip()
        if not target:
            raise RuntimeError("keyring secret ref must be service:username")
        if ":" not in target:
            raise RuntimeError("keyring secret ref must be service:username")
        service, username = target.split(":", 1)
        if not service or not username:
            raise RuntimeError("keyring secret ref must be service:username")
        try:
            import keyring  # type: ignore
        except Exception as exc:
            raise RuntimeError(
                "keyring provider requested but python package 'keyring' is unavailable"
            ) from exc
        value = keyring.get_password(service, username)
        if value is None:
            raise RuntimeError(f"keyring secret not found for {service}:{username}")
        return value
    raise RuntimeError(f"unknown secret source: {source}")
