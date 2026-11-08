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


def test_classify_fence_activation_accepts_pure_write_fence():
    result = classify_fence_activation(_fence("python write path=src/example.py"))
    assert result.status == "active"
    assert result.language == "python"
    assert result.predicate == "explicit-write"
    assert result.path == "src/example.py"
    assert result.has_write is True
    assert result.has_exec is False


def test_classify_fence_activation_pure_write_is_open_over_unregistered_languages():
    result = classify_fence_activation(_fence("rust write path=src/main.rs"))
    assert result.status == "active"
    assert result.language == "rust"
    assert result.predicate == "explicit-write"
    assert result.path == "src/main.rs"
    assert result.has_write is True
    assert result.has_exec is False


def test_classify_fence_activation_accepts_composite_write_and_exec():
    result = classify_fence_activation(_fence("python write path=scripts/migrate.py exec"))
    assert result.status == "active"
    assert result.language == "python"
    assert result.predicate == "explicit-write-exec"
    assert result.path == "scripts/migrate.py"
    assert result.has_write is True
    assert result.has_exec is True


def test_classify_fence_activation_rejects_write_without_path_or_empty_path():
    no_path = classify_fence_activation(_fence("python write"))
    empty_path = classify_fence_activation(_fence("python write path="))

    assert no_path.status == "unsupported"
    assert no_path.reason == "write fence requires path attribute"
    assert empty_path.status == "unsupported"
    assert empty_path.reason == "path value is empty"


def test_classify_fence_activation_rejects_repeated_verbs():
    result = classify_fence_activation(_fence("python write write path=foo.py"))
    assert result.status == "unsupported"
    assert result.reason == "activation form repeats a verb"


def test_classify_fence_activation_accepts_io_channels():
    result = classify_fence_activation(
        _fence("python exec stdin=ib_data123 out=artifacts/build.log err=artifacts/build.err append_out=true append_err=false")
    )
    assert result.status == "active"
    assert result.stdin == "ib_data123"
    assert result.out == "artifacts/build.log"
    assert result.err == "artifacts/build.err"
    assert result.append_out is True
    assert result.append_err is False


def test_classify_fence_activation_accepts_io_channels_on_explicit_runtime():
    result = classify_fence_activation(
        _fence("bc exec runtime=bc stdin=input.txt out=output.txt err=error.txt append_out=false append_err=true")
    )
    assert result.status == "active"
    assert result.predicate == "explicit-runtime"
    assert result.stdin == "input.txt"
    assert result.out == "output.txt"
    assert result.err == "error.txt"
    assert result.append_out is False
    assert result.append_err is True


def test_classify_fence_activation_rejects_empty_io_channels():
    empty_stdin = classify_fence_activation(_fence("python exec stdin="))
    empty_out = classify_fence_activation(_fence("python exec out="))
    empty_err = classify_fence_activation(_fence("python exec err="))

    assert empty_stdin.status == "unsupported"
    assert empty_stdin.reason == "stdin value is empty"
    assert empty_out.status == "unsupported"
    assert empty_out.reason == "out value is empty"
    assert empty_err.status == "unsupported"
    assert empty_err.reason == "err value is empty"


def test_classify_fence_activation_validates_append_flags():
    no_out = classify_fence_activation(_fence("python exec append_out=true"))
    no_err = classify_fence_activation(_fence("python exec append_err=true"))
    bad_out = classify_fence_activation(_fence("python exec out=out.txt append_out=maybe"))
    bad_err = classify_fence_activation(_fence("python exec err=err.txt append_err=invalid"))

    assert no_out.status == "unsupported"
    assert no_out.reason == "append_out requires out attribute"
    assert no_err.status == "unsupported"
    assert no_err.reason == "append_err requires err attribute"
    assert bad_out.status == "unsupported"
    assert bad_out.reason == "append_out must be true or false"
    assert bad_err.status == "unsupported"
    assert bad_err.reason == "append_err must be true or false"

