import json

from toas.runtime.spill_telemetry import aggregate_spill_telemetry, aggregate_spill_telemetry_file


def _line(record):
    return json.dumps(record)


def _result(related_to, tool, telemetry, *, content="RAW_PRIVATE_OUTPUT"):
    return {
        "kind": "tool_result",
        "related_to": related_to,
        "payload": {
            "tool_name": tool,
            "content": content,
        },
        "spill_telemetry": [telemetry],
    }


def _telemetry(result_id, outputs=(), *, read_block_id=None):
    value = {"schema": "spill_observation.v0", "coverage": "complete", "result_id": result_id, "outputs": list(outputs)}
    if read_block_id is not None:
        value["read_block_id"] = read_block_id
    return value


def _output(observation_id, tool, lines, byte_count, *, spilled=False, block_id=None):
    value = {
        "observation_id": observation_id,
        "tool_name": tool,
        "original_lines": lines,
        "original_bytes": byte_count,
        "spilled": spilled,
    }
    if block_id is not None:
        value["block_id"] = block_id
    return value


def test_aggregate_telemetry_is_bounded_deduplicated_and_matches_only_prior_exact_ids():
    spilled = _result(
        "message-one", "shell", _telemetry("result-one", [_output("obs-one", "shell", 51, 5000, spilled=True, block_id="ib_known")]),
    )
    future_reference = {
        "kind": "tool_request", "related_to": "message-two",
        "payload": [{"tool_name": "shell", "args": {"argv": ["cat", "ib_future"]}}],
    }
    future_spill = _result(
        "message-three", "mystery-secret-tool",
        _telemetry("result-future", [_output("obs-future", "mystery-secret-tool", 2, 20, spilled=True, block_id="ib_future")]),
    )
    same_origin_reference = {
        "kind": "tool_request", "related_to": "message-one",
        "payload": [{"tool_name": "shell", "args": {"argv": ["cat", "ib_known.txt"]}}],
    }
    request = {
        "kind": "tool_request", "related_to": "message-four",
        "payload": [
            {"tool_name": "shell", "args": {"argv": ["cat", ".toas/scratch/ib_known.txt"], "secret": "REQUEST_SECRET"}},
            {"tool_name": "shell_script", "args": {"script": "cat ib_known"}},
            {"tool_name": "shell", "args": {"command": "cat ib_unknown"}},
        ],
    }
    unrelated_tool_reference = {
        "kind": "tool_request", "related_to": "echo-message",
        "payload": [{"tool_name": "echo", "args": {"text": "ib_known"}}],
    }
    read_request = {
        "kind": "tool_request", "related_to": "message-five",
        "payload": [{"tool_name": "read_file", "args": {"path": ".toas/scratch/ib_known.txt"}}],
    }
    read_result = _result("message-five", "read_file", _telemetry("result-read", read_block_id="ib_known"))
    legacy = {"kind": "tool_result", "related_to": "old-message", "payload": {"tool_name": "shell", "content": "LEGACY_SECRET"}}
    command_request = {
        "kind": "command_request", "related_to": "message-six",
        "payload": {"id": "command-six", "command": "cat .toas/scratch/ib_known.txt", "args": []},
    }
    command_result = {
        "kind": "command_result", "related_to": "command-six",
        "payload": {"content": "DIRECT_OUTPUT_SECRET"},
        "spill_telemetry": [_telemetry("result-direct", [_output("obs-direct", "shell", 4, 40)])],
    }
    report = aggregate_spill_telemetry(map(_line, [
        spilled, dict(spilled), future_reference, future_spill, same_origin_reference, request,
        unrelated_tool_reference, read_request, read_result, legacy, command_request, command_result,
    ]))

    assert report["schema"] == "spill_telemetry.v0"
    assert report["coverage"] == {
        "result_records": 5,
        "observed_result_records": 4,
        "unobserved_result_records": 1,
    }
    assert report["tools"]["shell"]["eligible_outputs"] == 2
    assert report["tools"]["shell"]["spill_count"] == 1
    assert report["tools"]["shell"]["unobserved_result_records"] == 1
    assert report["tools"]["shell"]["spill_line_distribution"]["41_100"] == 1
    assert report["tools"]["shell"]["spill_byte_distribution"]["4k_16k"] == 1
    assert report["tools"]["other"]["eligible_outputs"] == 1
    assert report["rereads"]["reference_pairs"] == 3
    assert report["rereads"]["read_file_confirmed_pairs"] == 1
    assert report["rereads"]["by_tool"] == {"read_file": 1, "shell": 2, "shell_script": 0, "other": 0}
    exported = json.dumps(report)
    for secret in ("RAW_PRIVATE_OUTPUT", "REQUEST_SECRET", "LEGACY_SECRET", "DIRECT_OUTPUT_SECRET", "ib_known", "message-four"):
        assert secret not in exported


def test_aggregate_telemetry_ignores_malformed_and_duplicate_observations(tmp_path):
    request = {"kind": "tool_request", "related_to": "m", "payload": {"malformed": True}}
    observation = _telemetry("r", [
        None,
        {"observation_id": "invalid-lines", "tool_name": "shell", "original_lines": True, "original_bytes": 1},
        {"observation_id": "invalid-bytes", "tool_name": "shell", "original_lines": 1, "original_bytes": False},
        {"observation_id": "valid", "tool_name": "unknown-sensitive-name", "original_lines": 0, "original_bytes": 0, "spilled": True, "block_id": 7},
        {"observation_id": "valid", "tool_name": "shell", "original_lines": 2, "original_bytes": 2, "spilled": True, "block_id": "ib_duplicate"},
        {"tool_name": "shell", "original_lines": 3, "original_bytes": 3},
    ])
    observation["outputs"] = observation["outputs"] + ["not an observation"]
    result = _result("m", "shell", observation)
    bad_outputs = {"schema": "spill_observation.v0", "result_id": "r2", "outputs": None}
    bad_record = {"kind": "tool_result", "spill_telemetry": [None, bad_outputs]}
    events = [
        "not-json", "[]", None,
        _line({"kind": "anchor", "payload": {}}),
        _line(request), _line(request),
        _line({"kind": "tool_request", "payload": {"not": "a list"}}),
        _line({"kind": "tool_request", "payload": [{"tool_name": "shell", "args": 42}]}),
        _line(result), _line(bad_record),
    ]

    report = aggregate_spill_telemetry(events)
    assert report["coverage"]["result_records"] == 2
    assert report["coverage"]["observed_result_records"] == 2
    assert report["tools"]["other"]["eligible_outputs"] == 1
    assert report["tools"]["other"]["spill_count"] == 1
    assert report["tools"]["shell"]["eligible_outputs"] == 0

    path = tmp_path / "events.jsonl"
    path.write_text(_line(result) + "\n", encoding="utf-8")
    assert aggregate_spill_telemetry_file(path)["tools"]["other"]["eligible_outputs"] == 1
