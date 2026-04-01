from dataclasses import dataclass


@dataclass(frozen=True)
class Tool:
    name: str
    required_args: tuple[str, ...]
    runner: callable


def _run_echo(args: dict) -> str:
    return args["text"]


REGISTRY = {
    "echo": Tool(
        name="echo",
        required_args=("text",),
        runner=_run_echo,
    )
}


def get_tool(name: str) -> Tool:
    try:
        return REGISTRY[name]
    except KeyError as exc:
        raise RuntimeError(f"unknown tool: {name}") from exc
