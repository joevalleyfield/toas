import json
from typing import Any

PROTOCOL_VERSION = 1


class RpcProtocolError(RuntimeError):
    pass


def encode_message(message: dict[str, Any]) -> bytes:
    return (json.dumps(message, ensure_ascii=False) + "\n").encode("utf-8")


def decode_message(line: bytes) -> dict[str, Any]:
    try:
        decoded = line.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RpcProtocolError("invalid utf-8 rpc message") from exc

    if not decoded.endswith("\n"):
        raise RpcProtocolError("rpc message must end with newline")

    raw = decoded[:-1]
    if not raw:
        raise RpcProtocolError("empty rpc message")

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RpcProtocolError("invalid json rpc message") from exc

    if not isinstance(parsed, dict):
        raise RpcProtocolError("rpc message must be a json object")
    return parsed


def make_request(request_id: str, op: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if payload is None:
        payload = {}
    return {
        "protocol_version": PROTOCOL_VERSION,
        "request_id": request_id,
        "op": op,
        "payload": payload,
    }


def make_ok_response(request_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if payload is None:
        payload = {}
    return {
        "protocol_version": PROTOCOL_VERSION,
        "request_id": request_id,
        "ok": True,
        "payload": payload,
    }


def make_error_response(request_id: str, *, code: str, message: str) -> dict[str, Any]:
    return {
        "protocol_version": PROTOCOL_VERSION,
        "request_id": request_id,
        "ok": False,
        "error": {
            "code": code,
            "message": message,
        },
    }


def validate_request(message: dict[str, Any]) -> dict[str, Any]:
    version = message.get("protocol_version")
    if version != PROTOCOL_VERSION:
        raise RpcProtocolError(f"unsupported protocol version: {version}")

    request_id = message.get("request_id")
    if not isinstance(request_id, str) or not request_id:
        raise RpcProtocolError("request_id must be a non-empty string")

    op = message.get("op")
    if not isinstance(op, str) or not op:
        raise RpcProtocolError("op must be a non-empty string")

    payload = message.get("payload", {})
    if not isinstance(payload, dict):
        raise RpcProtocolError("payload must be a json object")

    return {
        "request_id": request_id,
        "op": op,
        "payload": payload,
    }


def validate_response(message: dict[str, Any], *, expected_request_id: str | None = None) -> dict[str, Any]:
    version = message.get("protocol_version")
    if version != PROTOCOL_VERSION:
        raise RpcProtocolError(f"unsupported protocol version: {version}")

    request_id = message.get("request_id")
    if not isinstance(request_id, str) or not request_id:
        raise RpcProtocolError("response request_id must be a non-empty string")
    if expected_request_id is not None and request_id != expected_request_id:
        raise RpcProtocolError(
            f"response request_id mismatch: expected {expected_request_id}, got {request_id}"
        )

    ok = message.get("ok")
    if not isinstance(ok, bool):
        raise RpcProtocolError("response ok must be a boolean")

    if ok:
        payload = message.get("payload", {})
        if not isinstance(payload, dict):
            raise RpcProtocolError("response payload must be a json object")
        return {"ok": True, "request_id": request_id, "payload": payload}

    error = message.get("error")
    if not isinstance(error, dict):
        raise RpcProtocolError("response error must be a json object")
    code = error.get("code")
    msg = error.get("message")
    if not isinstance(code, str) or not code:
        raise RpcProtocolError("response error.code must be a non-empty string")
    if not isinstance(msg, str) or not msg:
        raise RpcProtocolError("response error.message must be a non-empty string")
    return {"ok": False, "request_id": request_id, "error": {"code": code, "message": msg}}
