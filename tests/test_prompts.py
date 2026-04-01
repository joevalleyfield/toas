import pytest

from toas.prompts import generation_messages, load_prompt, prompt_messages


def test_load_prompt_reads_generation_asset():
    content = load_prompt("generation", version="v1")

    assert "TOAS" in content
    assert "next assistant message content" in content


def test_generation_messages_prepends_system_prompt():
    messages = generation_messages([{"role": "user", "content": "hello"}], version="v1")

    assert messages[0]["role"] == "system"
    assert "TOAS" in messages[0]["content"]
    assert messages[1:] == [{"role": "user", "content": "hello"}]


def test_prompt_messages_support_protocol_assets():
    messages = prompt_messages("protocol", [{"role": "user", "content": "hello"}], version="terse_v1")

    assert messages[0]["role"] == "system"
    assert "TOAS" in messages[0]["content"]
    assert "action" in messages[0]["content"]
    assert messages[1:] == [{"role": "user", "content": "hello"}]


def test_load_prompt_rejects_missing_asset():
    with pytest.raises(RuntimeError, match="missing prompt: generation/missing"):
        load_prompt("generation", version="missing")
