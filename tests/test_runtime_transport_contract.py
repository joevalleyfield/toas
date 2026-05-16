import pytest

from toas.runtime.transport_contract import EnvelopeMessage, envelope_message_from_dict


def test_envelope_message_valid_minimal_shape():
    msg = EnvelopeMessage(
        session_id="s1",
        activity_id="a1",
        event_id=0,
        kind="status",
        ts="2026-05-16T00:00:00Z",
        payload={"state": "running"},
    )
    assert msg.final is False
    assert msg.cancel_of is None


@pytest.mark.parametrize(
    "kwargs,error",
    [
        ({"session_id": "", "activity_id": "a1", "event_id": 0, "kind": "k", "ts": "t", "payload": {}}, "session_id"),
        ({"session_id": "s1", "activity_id": "", "event_id": 0, "kind": "k", "ts": "t", "payload": {}}, "activity_id"),
        ({"session_id": "s1", "activity_id": "a1", "event_id": -1, "kind": "k", "ts": "t", "payload": {}}, "event_id"),
        ({"session_id": "s1", "activity_id": "a1", "event_id": 0, "kind": "", "ts": "t", "payload": {}}, "kind"),
        ({"session_id": "s1", "activity_id": "a1", "event_id": 0, "kind": "k", "ts": "", "payload": {}}, "ts"),
        ({"session_id": "s1", "activity_id": "a1", "event_id": 0, "kind": "k", "ts": "t", "payload": []}, "payload"),
        (
            {
                "session_id": "s1",
                "activity_id": "a1",
                "event_id": 0,
                "kind": "k",
                "ts": "t",
                "payload": {},
                "cancel_of": "",
            },
            "cancel_of",
        ),
    ],
)
def test_envelope_message_validates_fields(kwargs, error):
    with pytest.raises(ValueError, match=error):
        EnvelopeMessage(**kwargs)


def test_envelope_message_from_dict_coerces_and_defaults():
    msg = envelope_message_from_dict(
        {
            "session_id": "s2",
            "activity_id": "a2",
            "event_id": 5,
            "kind": "result",
            "ts": "2026-05-16T01:02:03Z",
            "payload": {"ok": True},
            "final": True,
            "cancel_of": "a1",
        }
    )
    assert msg.event_id == 5
    assert msg.kind == "result"
    assert msg.final is True
    assert msg.cancel_of == "a1"

