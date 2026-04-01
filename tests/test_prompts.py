import pytest

from toas.prompts import list_prompt_assets, load_prompt, load_prompt_asset, load_prompt_ref, parse_prompt_ref, prompt_messages


def test_load_prompt_reads_named_asset():
    content = load_prompt("generation", "v1")

    assert "TOAS" in content
    assert "next assistant message content" in content


def test_load_prompt_ref_reads_path_like_identifier():
    content = load_prompt_ref("protocol/terse_v1")

    assert "TOAS" in content
    assert "action" in content


def test_load_prompt_asset_reads_metadata_backed_session_prompt():
    asset = load_prompt_asset("session-start/start-here/blank-page_v1")

    assert asset.ref == "session-start/start-here/blank-page_v1"
    assert asset.metadata == {
        "name": "Blank Page Starter",
        "description": "A simple opening prompt for when you do not know how to begin.",
        "category": "start-here",
    }
    assert "Help me get started" in asset.content


def test_list_prompt_assets_can_filter_by_prefix():
    assets = list_prompt_assets("session-start/role-framing")

    assert [asset.ref for asset in assets] == [
        "session-start/role-framing/editorial-partner_v1",
        "session-start/role-framing/pragmatic-engineer_v1",
        "session-start/role-framing/requirements-interrogator_v1",
    ]
    assert all(asset.metadata["category"] == "role-framing" for asset in assets)


def test_prompt_messages_support_protocol_assets():
    messages = prompt_messages("protocol", [{"role": "user", "content": "hello"}], version="terse_v1")

    assert messages[0]["role"] == "system"
    assert "TOAS" in messages[0]["content"]
    assert "action" in messages[0]["content"]
    assert messages[1:] == [{"role": "user", "content": "hello"}]


def test_parse_prompt_ref_rejects_invalid_refs():
    with pytest.raises(RuntimeError, match="invalid prompt ref: ../generation"):
        parse_prompt_ref("../generation")


def test_load_prompt_rejects_missing_asset():
    with pytest.raises(RuntimeError, match="missing prompt: generation/missing"):
        load_prompt("generation", "missing")
