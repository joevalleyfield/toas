"""Build reversible payload comparisons; no inference or runtime writes."""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def split_output(content: str) -> dict:
    match = re.fullmatch(
        r"(?P<outcome>\[OK\] shell: exit=0)\nstdout:\n"
        r"```text toas-output kind=stdout source=tool.shell potency=inert\n"
        r"(?P<body>.*)\n```", content, re.DOTALL,
    )
    if not match:
        raise ValueError("Unexpected captured output; do not guess a representation")
    return {
        "outcome_line": match["outcome"],
        "streams": [{
            "language": "text", "format": "toas-output", "kind": "stdout",
            "source": "tool.shell", "potency": "inert", "text": match["body"],
        }],
    }


def restore_output(content: dict) -> str:
    stream = content["streams"][0]
    text = stream.get("text")
    if text is None:
        text = "\n".join(f"{line['line_number']}:{line['text']}" for line in stream["line_matches"])
    return (
        content["outcome_line"] + "\n" + stream["kind"] + ":\n```"
        + stream["language"] + " " + stream["format"] + " kind=" + stream["kind"]
        + " source=" + stream["source"] + " potency=" + stream["potency"]
        + "\n" + text + "\n```"
    )


def result_messages(packet: dict) -> list[dict]:
    return [message for outcome in packet["observation"]["tool_outcomes"] for message in outcome["result"]]


def strip_backticks(value):
    if isinstance(value, str):
        return value.replace("`", "")
    if isinstance(value, list):
        return [strip_backticks(item) for item in value]
    if isinstance(value, dict):
        return {key: strip_backticks(item) for key, item in value.items()}
    return value


def embedded_json_paths(value, path="$", found=None):
    found = [] if found is None else found
    if isinstance(value, dict):
        for key, item in value.items():
            embedded_json_paths(item, path + "." + key, found)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            embedded_json_paths(item, f"{path}[{index}]", found)
    elif isinstance(value, str):
        try:
            decoded = json.loads(value)
        except ValueError:
            decoded = None
        if isinstance(decoded, (dict, list)):
            found.append(path)
    return found


def main() -> None:
    sdk = json.loads((ROOT / "docs/notes/2026-10-10-state-inference-sdk-request.json").read_text())
    clean = json.loads(sdk["messages"][0]["content"])
    clean["observation"].pop("control_results", None)
    nested_json = embedded_json_paths(clean)
    assert not nested_json, nested_json
    packets = {name: copy.deepcopy(clean) for name in [
        "json_clean", "pretty_packet", "unfenced_outputs", "structured_stdout",
        "structured_matches", "state_plaintext", "state_empty_plan", "no_tool_observations",
    ]}
    for original, unfenced, structured, matches in zip(
        result_messages(clean), result_messages(packets["unfenced_outputs"]),
        result_messages(packets["structured_stdout"]), result_messages(packets["structured_matches"]),
    ):
        content = original["content"]
        assert content.count("```") == 2
        unfenced["content"] = content.replace("```", "")
        structured["content"] = split_output(content)
        assert restore_output(structured["content"]) == content
        matches["content"] = split_output(content)
        stream = matches["content"]["streams"][0]
        stream["line_matches"] = []
        for line in stream.pop("text").splitlines():
            found = re.fullmatch(r"(\d+):(.*)", line)
            assert found, line
            stream["line_matches"].append({"line_number": int(found[1]), "text": found[2]})
        assert restore_output(matches["content"]) == content
    packets["state_plaintext"]["state"] = strip_backticks(clean["state"])
    packets["state_empty_plan"]["state"]["next_steps"] = []
    packets["no_tool_observations"]["observation"]["tool_outcomes"] = []
    arms = {}
    for name, packet in packets.items():
        assert all(packet[key] == clean[key] for key in ("instructions", "schema", "tools"))
        if name not in {"state_plaintext", "state_empty_plan"}:
            assert packet["state"] == clean["state"]
        arms[name] = [{"role": "user", "content": json.dumps(
            packet, ensure_ascii=False, indent=2 if name == "pretty_packet" else None,
        )}]
        assert "control_results" not in packet["observation"]
    assert arms["json_clean"] == [{"role": "user", "content": json.dumps(clean, ensure_ascii=False)}]
    (HERE / "variants.json").write_text(json.dumps(arms, ensure_ascii=False, indent=2) + "\n")
    (HERE / "inputs").mkdir(exist_ok=True)
    for name, messages in arms.items():
        (HERE / "inputs" / f"{name}.json").write_text(messages[0]["content"])
    (HERE / "inventory.json").write_text(json.dumps({
        "source_transition": "st_0fd3c8cc81064c2c86e8edb0a75d701e",
        "embedded_json_object_or_array_strings": nested_json,
        "markdown_fenced_output_paths": [
            "observation.tool_outcomes[0].result[0].content",
            "observation.tool_outcomes[1].result[0].content",
        ],
        "message_content_lengths": {name: len(messages[0]["content"]) for name, messages in arms.items()},
        "structured_output_roundtrip": "exact, including source line whitespace and output metadata",
    }, indent=2) + "\n")
    print("Built eight single-user-message conditions; structured outputs round-trip exactly")


if __name__ == "__main__":
    main()
