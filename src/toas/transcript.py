def parse_transcript(text: str) -> list[dict]:
    messages = []
    current_role = None
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_role, current_lines
        if not current_role:
            current_lines = []
            return

        messages.append(
            {
                "role": current_role,
                "content": "\n".join(current_lines).strip(),
            }
        )
        current_lines = []

    for line in text.splitlines():
        if line.startswith("## "):
            flush()
            role = line[3:].strip().lower()
            current_role = role or None
            continue

        if current_role is not None:
            current_lines.append(line)

    flush()
    return messages
