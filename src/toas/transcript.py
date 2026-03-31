
def parse_transcript(text: str) -> list[dict]:
    blocks = text.split("## ")
    out = []

    for b in blocks[1:]:
        lines = b.splitlines()
        role = lines[0].strip().lower()
        content = "\n".join(lines[1:]).strip()
        out.append({"role": role, "content": content})

    return out
