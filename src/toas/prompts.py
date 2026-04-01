from importlib import resources


DEFAULT_PROMPT_VERSION = "v1"


def load_prompt(kind: str, version: str = DEFAULT_PROMPT_VERSION) -> str:
    package = resources.files("toas").joinpath("prompts", kind, f"{version}.txt")
    try:
        return package.read_text(encoding="utf-8").strip()
    except FileNotFoundError as exc:
        raise RuntimeError(f"missing prompt: {kind}/{version}") from exc


def generation_messages(messages: list[dict], version: str = DEFAULT_PROMPT_VERSION) -> list[dict]:
    return [
        {"role": "system", "content": load_prompt("generation", version=version)},
        *messages,
    ]
