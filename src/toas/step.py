import re

import yaml

from .transcript import parse_transcript


def _eq(a, b):
    return (
        a["role"] == b["role"]
        and a["content"].strip() == b["content"].strip()
    )


def _lcp(a, b):
    i = 0
    for x, y in zip(a, b):
        if _eq(x, y):
            i += 1
        else:
            break
    return i


_YAML_BLOCK_RE = re.compile(r"```yaml\s*\n(.*?)\n```", re.DOTALL)


def _extract_plan(content: str):
    matches = _YAML_BLOCK_RE.findall(content)
    if not matches:
        return None

    try:
        plan = yaml.safe_load(matches[-1])
    except yaml.YAMLError:
        return None

    return plan


def _as_nodes(result) -> list[dict]:
    if not result:
        return []
    if isinstance(result, list):
        return result
    return [result]


def step(transcript: str, log: list[dict], generate=None, execute=None):
    generate = generate or (lambda _: None)
    execute = execute or (lambda _working, _plan: None)

    nodes = parse_transcript(transcript)

    i = _lcp(nodes, log)
    new_from_transcript = nodes[i:]

    working = log + new_from_transcript

    consequences = []
    if working:
        frontier = working[-1]
        plan = _extract_plan(frontier["content"])

        if plan is not None:
            consequences.extend(_as_nodes(execute(working, plan)))
        elif frontier["role"] == "user":
            consequences.extend(_as_nodes(generate(working)))

    return new_from_transcript + consequences, consequences
