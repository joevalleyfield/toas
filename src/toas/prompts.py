from importlib import resources


def parse_prompt_ref(ref: str) -> tuple[str, str]:
    if "/" not in ref:
        raise RuntimeError(f"invalid prompt ref: {ref}")
    kind, version = ref.split("/", 1)
    if not kind or not version:
        raise RuntimeError(f"invalid prompt ref: {ref}")
    return kind, version


def load_prompt(kind: str, version: str) -> str:
    package = resources.files("toas").joinpath("prompts", kind, f"{version}.txt")
    try:
        return package.read_text(encoding="utf-8").strip()
    except FileNotFoundError as exc:
        raise RuntimeError(f"missing prompt: {kind}/{version}") from exc


def load_prompt_ref(ref: str) -> str:
    kind, version = parse_prompt_ref(ref)
    return load_prompt(kind, version)


def prompt_messages(kind: str, messages: list[dict], version: str) -> list[dict]:
    return [
        {"role": "system", "content": load_prompt(kind, version=version)},
        *messages,
    ]
