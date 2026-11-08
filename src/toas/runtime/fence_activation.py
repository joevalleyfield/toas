"""Potency classification for structurally scanned Markdown fences."""
from __future__ import annotations

from dataclasses import dataclass

from .markdown_fence import MarkdownFence

_LANGUAGE_ALIASES = {
    "bash": "bash",
    "json": "json",
    "powershell": "powershell",
    "python": "python",
    "sh": "bash",
    "shell": "bash",
    "sql": "sql",
    "toas-tool": "toas-tool",
    "yaml": "yaml",
}


@dataclass(frozen=True)
class FenceActivation:
    """Lane-neutral result of deciding whether a fence claims execution or materialization."""

    status: str
    language: str | None
    predicate: str
    reason: str
    toolset: str | None = None
    path: str | None = None
    ref: str | None = None
    has_write: bool = False
    has_exec: bool = False
    stdin: str | None = None
    out: str | None = None
    err: str | None = None
    append_out: bool = False
    append_err: bool = False


_ALLOWED_ATTRIBUTES = {
    "append",
    "append_err",
    "append_out",
    "cwd",
    "err",
    "force",
    "mode",
    "out",
    "overwrite",
    "path",
    "persist",
    "ref",
    "runtime",
    "stdin",
    "timeout_s",
    "toolset",
}


def classify_fence_activation(fence: MarkdownFence | None) -> FenceActivation:
    if fence is None:
        return FenceActivation("malformed", None, "structure", "no closed fence was available")

    tokens = fence.info_tokens
    if not tokens:
        return FenceActivation("inert", None, "none", "no activation marker")
    language = tokens[0].casefold()
    if language in {"inert", "toas-output"} or "inert" in {token.casefold() for token in tokens[1:]}:
        return FenceActivation("inert", language, "explicit-inert", "explicit inert fence form")

    verb_tokens = [token.casefold() for token in tokens[1:] if "=" not in token]
    attr_tokens = [token for token in tokens[1:] if "=" in token]

    has_exec = "exec" in verb_tokens
    has_write = "write" in verb_tokens

    if not has_exec and not has_write:
        return FenceActivation("inert", language, "none", "no activation marker")

    if has_write and has_exec:
        predicate = "explicit-write-exec"
    elif has_write:
        predicate = "explicit-write"
    else:
        predicate = "explicit-exec"

    if any(verb not in {"exec", "write"} for verb in verb_tokens):
        return FenceActivation("unsupported", language, predicate, "activation form has extra tokens")

    if len(verb_tokens) != len(set(verb_tokens)):
        return FenceActivation("unsupported", language, predicate, "activation form repeats a verb")

    parsed_attributes: dict[str, str] = {}
    toolset = None
    if attr_tokens:
        for attr in attr_tokens:
            key, value = attr.split("=", 1)
            if key in parsed_attributes:
                return FenceActivation("unsupported", language, predicate, "activation form repeats an attribute")
            parsed_attributes[key] = value

        unknown_attributes = set(parsed_attributes) - _ALLOWED_ATTRIBUTES
        if unknown_attributes:
            return FenceActivation("unsupported", language, predicate, "activation form has unknown attributes")

        toolset = parsed_attributes.get("toolset")
        if "toolset" in parsed_attributes and not toolset:
            return FenceActivation("unsupported", language, predicate, "toolset value is empty")

    path_val = parsed_attributes.get("path")
    if path_val is not None and not path_val.strip():
        return FenceActivation("unsupported", language, predicate, "path value is empty")

    if has_write and not path_val:
        return FenceActivation("unsupported", language, predicate, "write fence requires path attribute")

    stdin_val = parsed_attributes.get("stdin")
    if "stdin" in parsed_attributes and (stdin_val is None or not stdin_val.strip()):
        return FenceActivation("unsupported", language, predicate, "stdin value is empty")

    out_val = parsed_attributes.get("out")
    if "out" in parsed_attributes and (out_val is None or not out_val.strip()):
        return FenceActivation("unsupported", language, predicate, "out value is empty")

    err_val = parsed_attributes.get("err")
    if "err" in parsed_attributes and (err_val is None or not err_val.strip()):
        return FenceActivation("unsupported", language, predicate, "err value is empty")

    append_out_val = False
    if "append_out" in parsed_attributes:
        if "out" not in parsed_attributes:
            return FenceActivation("unsupported", language, predicate, "append_out requires out attribute")
        raw_out = parsed_attributes["append_out"].casefold()
        if raw_out not in {"true", "false"}:
            return FenceActivation("unsupported", language, predicate, "append_out must be true or false")
        append_out_val = raw_out == "true"

    append_err_val = False
    if "append_err" in parsed_attributes:
        if "err" not in parsed_attributes:
            return FenceActivation("unsupported", language, predicate, "append_err requires err attribute")
        raw_err = parsed_attributes["append_err"].casefold()
        if raw_err not in {"true", "false"}:
            return FenceActivation("unsupported", language, predicate, "append_err must be true or false")
        append_err_val = raw_err == "true"

    canonical = _LANGUAGE_ALIASES.get(language)
    if has_exec:
        if canonical is None:
            if toolset is None and parsed_attributes.get("runtime"):
                return FenceActivation(
                    "active",
                    language,
                    "explicit-runtime",
                    "unregistered language with explicit runtime",
                    path=path_val,
                    ref=parsed_attributes.get("ref"),
                    has_write=has_write,
                    has_exec=True,
                    stdin=stdin_val,
                    out=out_val,
                    err=err_val,
                    append_out=append_out_val,
                    append_err=append_err_val,
                )
            return FenceActivation("unsupported", language, predicate, "language is not registered")
        if canonical in {"yaml", "json"} and toolset not in {None, "toas"}:
            return FenceActivation("unsupported", canonical, predicate, "toolset is not registered")
    else:
        canonical = canonical or language

    reason = (
        "explicit write and exec markers"
        if (has_write and has_exec)
        else ("explicit write marker" if has_write else "explicit exec marker")
    )
    return FenceActivation(
        "active",
        canonical,
        predicate,
        reason,
        toolset or ("toas" if canonical in {"yaml", "json"} else None),
        path=path_val,
        ref=parsed_attributes.get("ref"),
        has_write=has_write,
        has_exec=has_exec,
        stdin=stdin_val,
        out=out_val,
        err=err_val,
        append_out=append_out_val,
        append_err=append_err_val,
    )
