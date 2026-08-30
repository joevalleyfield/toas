from __future__ import annotations

from toas.runtime.fence_activation import classify_fence_activation
from toas.runtime.markdown_fence import scan_markdown_fences


def _fence(info: str):
    return scan_markdown_fences(f"```{info}\nbody\n```")[0]


def test_classify_fence_activation_accepts_registered_exec_language_alias():
    result = classify_fence_activation(_fence("sh exec"))

    assert result.status == "active"
    assert result.language == "bash"
    assert result.predicate == "explicit-exec"


def test_classify_fence_activation_defaults_structured_toolset_and_accepts_explicit_toas():
    implicit = classify_fence_activation(_fence("json exec"))
    explicit = classify_fence_activation(_fence("yaml exec toolset=toas"))

    assert implicit.toolset == "toas"
    assert explicit.status == "active"
    assert explicit.toolset == "toas"


def test_classify_fence_activation_rejects_unknown_structured_toolset():
    result = classify_fence_activation(_fence("json exec toolset=other"))

    assert result.status == "unsupported"


def test_classify_fence_activation_rejects_duplicate_unknown_and_empty_attributes():
    duplicate = classify_fence_activation(_fence("json exec toolset=toas toolset=toas"))
    unknown = classify_fence_activation(_fence("json exec mystery=value"))
    empty = classify_fence_activation(_fence("json exec toolset="))

    assert duplicate.reason == "activation form repeats an attribute"
    assert unknown.reason == "activation form has unknown attributes"
    assert empty.reason == "toolset value is empty"


def test_classify_fence_activation_rejects_blank_info_tokens():
    result = classify_fence_activation(_fence('json exec runtime="unterminated'))

    assert result.status == "inert"


def test_classify_fence_activation_leaves_ordinary_fence_inert():
    result = classify_fence_activation(_fence("yaml"))

    assert result.status == "inert"
    assert result.predicate == "none"


def test_classify_fence_activation_explicit_inert_wins():
    result = classify_fence_activation(_fence("yaml inert"))

    assert result.status == "inert"
    assert result.predicate == "explicit-inert"


def test_classify_fence_activation_rejects_unknown_or_ambiguous_exec_forms():
    unknown = classify_fence_activation(_fence("ruby exec"))
    extra = classify_fence_activation(_fence("bash exec extra"))

    assert unknown.status == "unsupported"
    assert extra.status == "unsupported"


def test_classify_fence_activation_allows_unknown_language_with_explicit_runtime():
    result = classify_fence_activation(_fence("bc exec runtime=bc"))

    assert result.status == "active"
    assert result.language == "bc"
    assert result.predicate == "explicit-runtime"


def test_classify_fence_activation_keeps_unknown_language_without_runtime_unsupported():
    result = classify_fence_activation(_fence("bc exec"))

    assert result.status == "unsupported"


def test_classify_fence_activation_treats_output_and_missing_structure_as_inert_or_malformed():
    output = classify_fence_activation(_fence("toas-output"))
    malformed = classify_fence_activation(None)

    assert output.status == "inert"
    assert malformed.status == "malformed"
