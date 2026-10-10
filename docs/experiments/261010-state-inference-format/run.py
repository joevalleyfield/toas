"""Diagnostic inference pilot; never executes proposed tools or persists runtime history."""
from __future__ import annotations

import argparse
import copy
import json
import random
import re
import time
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit

import yaml

from toas.cli_session_commands import _build_step_cli_deps, _resolve_runtime_generation_context
from toas.graph import read_log
from toas.llm import OpenAIDriver, get_client
from toas.runtime.state_step import _normalize_tool_call_aliases, _parse_state_response
from toas.tools import REGISTRY, validate_registered_call


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def variants() -> dict[str, list[dict]]:
    original = json.loads(
        (ROOT / "docs/notes/2026-10-10-state-inference-sdk-request.json").read_text()
    )["messages"]
    packet = json.loads(original[0]["content"])
    clean = copy.deepcopy(packet)
    clean["observation"].pop("control_results", None)
    data = {k: v for k, v in clean.items() if k != "instructions"}
    example = {
        "state_patch": {"notes": {"findings": ["The observed configuration names settings.yaml."]}},
        "tool_calls": [{"tool_name": "read_file", "args": {"path": "settings.yaml"}}],
        "outcome": "continue",
    }
    with_example = copy.deepcopy(clean)
    with_example["instructions"] += (
        "\n\nExample response for a DIFFERENT task (do not copy its facts or file path):\n"
        + json.dumps(example, indent=2)
    )
    prior = json.loads((HERE / "prior-accepted-exchange.json").read_text())["messages"]
    user = lambda p: [{"role": "user", "content": json.dumps(p, ensure_ascii=False)}]
    result = {
        "original_reference": original,
        "json_clean": user(clean),
        "split_json": [
            {"role": "system", "content": clean["instructions"]},
            {"role": "user", "content": json.dumps(data, ensure_ascii=False, indent=2)},
        ],
        "split_yaml": [
            {"role": "system", "content": clean["instructions"]},
            {"role": "user", "content": yaml.safe_dump(data, sort_keys=False, allow_unicode=True)},
        ],
        "json_example": user(with_example),
        "json_prior_turn": [*prior, *user(clean)],
    }
    assert "control_results" in packet["observation"]
    assert "control_results" not in clean["observation"]
    assert json.loads(prior[-1]["content"])["state_patch"]
    return result


def advertised_tool_names(messages: list[dict]) -> set[str]:
    for message in reversed(messages):
        content = message.get("content")
        if not isinstance(content, str):
            continue
        candidates = [content]
        start = content.find("{")
        if start > 0:
            candidates.append(content[start:])
        for candidate in candidates:
            try:
                packet = json.loads(candidate)
            except (ValueError, TypeError):
                try:
                    packet = yaml.safe_load(candidate)
                except yaml.YAMLError:
                    continue
            if not isinstance(packet, dict):
                continue
            tools = packet.get("tools")
            available = tools.get("available") if isinstance(tools, dict) else None
            if isinstance(available, list) and all(isinstance(name, str) for name in available):
                return set(available)
    raise ValueError("No captured tools.available list found in request messages")


def validate_proposal(value: object, advertised_tools: set[str]) -> tuple[bool, str]:
    if not isinstance(value, dict):
        return False, "proposal is not an object"
    if not isinstance(value.get("state_patch"), dict) or not isinstance(value.get("tool_calls"), list):
        return False, "explicit state_patch object and tool_calls array required"
    if value.get("outcome", "continue") not in {"continue", "complete"}:
        return False, "invalid outcome"
    if value.get("outcome") == "complete" and value["tool_calls"]:
        return False, "completion requests tools"
    if "report" in value and not isinstance(value["report"], str):
        return False, "report is not a string"
    if "continue_on_error" in value and not isinstance(value["continue_on_error"], bool):
        return False, "continue_on_error is not a boolean"
    try:
        calls = _normalize_tool_call_aliases(value["tool_calls"])
        for call in calls:
            if call["tool_name"] not in advertised_tools:
                return False, "unadvertised tool"
            validate_registered_call(REGISTRY, call)
    except (KeyError, TypeError, ValueError, RuntimeError) as exc:
        return False, str(exc)
    return True, ""


def evaluate(content: str, advertised_tools: set[str]) -> dict:
    parsed = None
    strict_parse = False
    try:
        parsed = _parse_state_response(content)
        strict_parse = True
    except (ValueError, TypeError):
        pass
    strict_valid, strict_reason = validate_proposal(parsed, advertised_tools)
    candidates = []
    if strict_parse:
        candidates = [parsed]
    else:
        # Diagnostic metric only, not a proposed production response parser.
        decoder = json.JSONDecoder()
        for match in re.finditer(r"(?m)^[ \t]*(?=\{)", content):
            start = match.end()
            try:
                candidate, end = decoder.raw_decode(content[start:])
            except ValueError:
                continue
            if isinstance(candidate, dict) and "state_patch" in candidate:
                candidates.append((candidate, content[start + end :].strip()))
    proposal = None
    if strict_parse:
        proposal = parsed
    elif len(candidates) == 1 and candidates[0][1] in {"", "```"}:
        proposal = candidates[0][0]
    valid, reason = validate_proposal(proposal, advertised_tools)
    return {
        "current_parser_json": strict_parse,
        "strict_valid_proposal": strict_valid,
        "valid_proposal_after_prose": valid,
        "proposal_error": reason if not valid else "",
        "strict_error": strict_reason if not strict_valid else "",
        "xml_tool_syntax": "<tool_call>" in content,
        "nonempty_state_patch": isinstance(proposal, dict) and bool(proposal.get("state_patch")),
        "proposal": proposal,
    }


def self_check() -> None:
    valid = '{"state_patch":{"notes":{"x":1}},"tool_calls":[]}'
    tools = {"read_file", "replace_block", "shell", "write_file"}
    assert evaluate(valid, tools)["strict_valid_proposal"]
    assert evaluate('{"state_patch":{},"tool_calls":[{"tool_name":"read_file","args":{"path":"src/toas/cli.py"}}]}', tools)["strict_valid_proposal"]
    assert evaluate("Reasoning.\n```json\n" + valid + "\n```", tools)["valid_proposal_after_prose"]
    assert evaluate("Reasoning.\n\n" + valid, tools)["valid_proposal_after_prose"]
    assert not evaluate("Reasoning.\n<tool_call>shell</tool_call>", tools)["valid_proposal_after_prose"]
    assert not evaluate('{"tool_calls":[]}', tools)["strict_valid_proposal"]
    assert not evaluate('[]', tools)["strict_valid_proposal"]
    assert not evaluate('{"state_patch":{},"tool_calls":[{"tool_name":"read_file","args":{}}]}', tools)["strict_valid_proposal"]
    assert not evaluate("Two proposals.\n" + valid + "\n" + valid, tools)["valid_proposal_after_prose"]
    assert evaluate('{"state_patch":{},"tool_calls":[{"tool_name":"search","args":{"query":"hello"}}]}', tools | {"search"})["strict_valid_proposal"]
    assert not evaluate('{"state_patch":{},"tool_calls":[{"tool_name":"search","args":{"query":"hello"}}]}', tools)["strict_valid_proposal"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rounds", type=int, default=2)
    parser.add_argument("--max-tokens", type=int, default=1800)
    parser.add_argument("--offline-check", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=HERE)
    parser.add_argument("--start-round", type=int, default=1)
    parser.add_argument("--counts", nargs="*", help="Selected condition counts, e.g. split_json=18 json_clean=8")
    parser.add_argument("--variant-file", type=Path, help="Explicit diagnostic condition messages; must include json_clean baseline")
    parser.add_argument("--source-transition", help="Captured transition represented by an explicit variant file")
    args = parser.parse_args()
    self_check()
    arms = variants()
    if args.variant_file:
        arms = json.loads(args.variant_file.read_text())
        if not isinstance(arms, dict) or "json_clean" not in arms:
            raise ValueError("Condition file must contain json_clean baseline")
        for messages in arms.values():
            if not isinstance(messages, list) or not messages or any(
                not isinstance(message, dict)
                or message.get("role") not in {"system", "user", "assistant"}
                or not isinstance(message.get("content"), str)
                for message in messages
            ):
                raise ValueError("Condition messages require supported roles and text content")
    counts = {name: args.rounds for name in arms}
    if args.counts:
        counts = {name: int(count) for name, count in (value.split("=", 1) for value in args.counts)}
        if any(name not in arms or count < 1 for name, count in counts.items()):
            raise ValueError("Unknown condition or nonpositive count")
    output = args.output_dir.resolve()
    if args.offline_check:
        print("offline evaluator and variant checks passed", flush=True)
        return
    events_path = Path(".toas/events.jsonl")
    _, _, runner, _ = _resolve_runtime_generation_context(
        deps=_build_step_cli_deps(), events_path=events_path, events=read_log(str(events_path))
    )
    source_packet = json.loads(arms["json_clean"][0]["content"])
    plan = runner.prepare_state_request(source_packet)
    destination = urlsplit(plan.selected_settings.llm_base_url)
    if destination.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise RuntimeError("This pilot is authorized only for the configured loopback model server")
    client = get_client(plan.selected_settings).with_options(max_retries=0, timeout=120)
    output.mkdir(parents=True, exist_ok=True)
    manifest = {
        "source_transition": args.source_transition or "st_0fd3c8cc81064c2c86e8edb0a75d701e",
        "model": plan.selected_settings.llm_model,
        "provider": plan.selected_settings.llm_provider,
        "destination": {"host": destination.hostname, "port": destination.port, "path": destination.path},
        "transport": plan.selected_settings.llm_transport_mode,
        "stream": plan.selected_settings.llm_stream_mode,
        "generation_extra_body": plan.generation.extra_body,
        "max_tokens": args.max_tokens,
        "rounds": max(counts.values()),
        "condition_counts": counts,
        "start_round": args.start_round,
        "order": [],
        "network_retries": 0,
        "tools_executed": False,
        "variant_file": str(args.variant_file.resolve()) if args.variant_file else None,
    }
    results = []
    for round_index in range(max(counts.values())):
        order = [name for name, count in counts.items() if count > round_index]
        random.Random(261010 + round_index + args.start_round - 1).shuffle(order)
        for name in order:
            run_id = f"r{round_index + args.start_round}-{name}"
            manifest["order"].append(run_id)
            (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
            captured = {}
            finish_reasons = []

            class RecordingStream:
                def __init__(self, stream):
                    self.stream = stream

                def __iter__(self):
                    for chunk in self.stream:
                        for choice in chunk.choices:
                            if choice.finish_reason:
                                finish_reasons.append(choice.finish_reason)
                        yield chunk

                def close(self):
                    self.stream.close()

            def create(**kwargs):
                captured.update(copy.deepcopy(kwargs))
                (output / f"{run_id}.sdk-request.json").write_text(
                    json.dumps(captured, ensure_ascii=False, indent=2) + "\n"
                )
                response = client.chat.completions.create(**kwargs)
                if kwargs.get("stream"):
                    return RecordingStream(response)
                finish_reasons.extend(c.finish_reason for c in response.choices if c.finish_reason)
                return response

            interceptor = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
            started = time.monotonic()
            print("START", run_id, flush=True)
            record = {"run_id": run_id, "variant": name, "round": round_index + args.start_round}
            try:
                response = OpenAIDriver().call(
                    arms[name], settings=plan.selected_settings,
                    extra_body=plan.generation.extra_body, max_tokens=args.max_tokens,
                    client=interceptor,
                )
                content = response.content
                (output / f"{run_id}.response.txt").write_text(content)
                advertised = advertised_tool_names(arms[name])
                record.update(evaluate(content, advertised))
                record["advertised_tools"] = sorted(advertised)
                record.update({"returned_model": response.model, "usage": response.usage,
                               "finish_reasons": finish_reasons})
                print("DONE", run_id, "strict", record["strict_valid_proposal"],
                      "prefix", record["valid_proposal_after_prose"],
                      "xml", record["xml_tool_syntax"], flush=True)
            except Exception as exc:
                record["error"] = str(exc)
                print("ERROR", run_id, type(exc).__name__, str(exc)[:180], flush=True)
                if not results:
                    results.append(record)
                    (output / "results.json").write_text(json.dumps(results, indent=2) + "\n")
                    raise
            record["duration_s"] = round(time.monotonic() - started, 3)
            results.append(record)
            (output / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n")
    client.close()


if __name__ == "__main__":
    main()
