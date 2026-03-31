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


def step(transcript: str, log: list[dict], generate=None):
    generate = generate or (lambda _: None)

    nodes = parse_transcript(transcript)

    i = _lcp(nodes, log)
    new_from_transcript = nodes[i:]

    working = log + new_from_transcript

    generated = []
    if nodes and nodes[-1]["role"] == "user":
        g = generate(working)
        if g:
            generated.append(g)

    return new_from_transcript + generated, generated
