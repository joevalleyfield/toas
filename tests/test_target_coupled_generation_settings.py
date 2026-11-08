from __future__ import annotations

import time
from dataclasses import replace
from unittest.mock import MagicMock

import pytest

from toas import cli
from toas.backend_policy import default_backend_policy
from toas.config import (
    EndpointCatalogEntry,
    EndpointRateLimitPolicy,
    GenerationPolicy,
    LLMPolicy,
    OperatorConfig,
    TargetCatalogEntry,
    TargetGenerationOverrides,
    config_from_file,
)
from toas.llm import NO_THINKING, Settings
from toas.runtime import step_generation_runtime as sgr
from toas.runtime.endpoint_throttler import EndpointThrottler
from toas.runtime.model_invocation_contracts import resolve_model_invocation
from toas.runtime.model_targets import (
    resolve_endpoint_generation,
    resolve_model_target,
    resolve_target_generation,
    resolve_target_invocation,
)
from toas.runtime.operator_command_config_help import _handle_config_command
from toas.runtime.operator_command_context import OperatorCommandContext
from toas.runtime.policy_edges import serialize_operator_config_toml


def _make_context(config: OperatorConfig, events: list[dict] | None = None, working: list[dict] | None = None) -> OperatorCommandContext:
    return OperatorCommandContext(
        execute=None,
        generate=None,
        events=events or [],
        working=working or [],
        frontier_role="user",
        transcript="",
        command_cwd=".",
        previous_command_cwd=None,
        workspace_mode="strict",
        workspace_roots=[],
        config=config,
        config_sources={},
        already_executed_indices=None,
    )


# ---------------------------------------------------------------------------
# 1. Three-Tier Generation Hierarchy Precedence
# ---------------------------------------------------------------------------

def test_three_tier_generation_hierarchy_target_overrides_endpoint_and_global():
    config = OperatorConfig(
        generation=GenerationPolicy(
            thinking_mode="disabled",
            thinking_budget_tokens=0,
            max_tokens=1000,
            transport_mode="chat_messages",
            max_retries=1,
            retry_delay_s=0.5,
        ),
        llm=LLMPolicy(
            endpoints=(
                EndpointCatalogEntry(
                    id="ep-reasoning",
                    base_url="http://reasoning:8000/v1",
                    generation=TargetGenerationOverrides(
                        thinking_mode="enabled",
                        thinking_budget_tokens=2048,
                        transport_mode="single_user_blob",
                    ),
                    rate_limit=EndpointRateLimitPolicy(min_interval_s=1.0),
                ),
            ),
            targets=(
                # Target overrides budget, inherits endpoint thinking_mode & transport_mode, and global max_tokens
                TargetCatalogEntry(
                    id="target-custom-budget",
                    endpoint="ep-reasoning",
                    generation=TargetGenerationOverrides(thinking_budget_tokens=4096),
                ),
                # Target explicitly disables thinking, overriding endpoint default
                TargetCatalogEntry(
                    id="target-disable-thinking",
                    endpoint="ep-reasoning",
                    generation=TargetGenerationOverrides(thinking_mode="disabled", thinking_budget_tokens=0),
                ),
            ),
        ),
    )

    # 1. Endpoint defaults over global config
    endpoint = config.llm.endpoints[0]
    ep_gen = resolve_endpoint_generation(config, endpoint)
    assert ep_gen.thinking_mode == "enabled"
    assert ep_gen.thinking_budget_tokens == 2048
    assert ep_gen.transport_mode == "single_user_blob"
    assert ep_gen.max_tokens == 1000  # from global
    assert ep_gen.max_retries == 1    # from global

    # 2. Target custom budget overrides endpoint
    t1 = resolve_model_target(config, "target-custom-budget")
    assert t1 is not None
    t1_gen = resolve_target_generation(config, t1)
    assert t1_gen.thinking_mode == "enabled"          # from endpoint
    assert t1_gen.thinking_budget_tokens == 4096     # from target override
    assert t1_gen.transport_mode == "single_user_blob" # from endpoint
    assert t1_gen.max_tokens == 1000                  # from global

    # 3. Target disabling thinking overrides endpoint
    t2 = resolve_model_target(config, "target-disable-thinking")
    assert t2 is not None
    t2_gen = resolve_target_generation(config, t2)
    assert t2_gen.thinking_mode == "disabled"         # from target override
    assert t2_gen.thinking_budget_tokens == 0        # from target override
    assert t2_gen.transport_mode == "single_user_blob" # from endpoint


def test_target_without_endpoint_falls_back_to_global():
    config = OperatorConfig(
        generation=GenerationPolicy(thinking_mode="disabled", max_tokens=1024),
        llm=LLMPolicy(
            targets=(
                TargetCatalogEntry(
                    id="standalone-target",
                    generation=TargetGenerationOverrides(thinking_mode="enabled", thinking_budget_tokens=1024),
                ),
            ),
        ),
    )
    t = resolve_model_target(config, "standalone-target")
    assert t is not None
    gen = resolve_target_generation(config, t)
    assert gen.thinking_mode == "enabled"
    assert gen.thinking_budget_tokens == 1024
    assert gen.max_tokens == 1024


# ---------------------------------------------------------------------------
# 2. Seamless Switching & Automatic Profile Flipping
# ---------------------------------------------------------------------------

def test_resolve_target_invocation_adjusts_payload_and_extra_body():
    config = OperatorConfig(
        generation=GenerationPolicy(thinking_mode="disabled", thinking_budget_tokens=0),
        llm=LLMPolicy(
            endpoints=(
                EndpointCatalogEntry(
                    id="ep1",
                    base_url="http://ep1/v1",
                    generation=TargetGenerationOverrides(thinking_mode="disabled"),
                ),
            ),
            targets=(
                TargetCatalogEntry(
                    id="fast",
                    endpoint="ep1",
                    model="model-fast",
                    generation=TargetGenerationOverrides(thinking_mode="disabled"),
                ),
                TargetCatalogEntry(
                    id="reasoning",
                    endpoint="ep1",
                    model="model-reasoning",
                    generation=TargetGenerationOverrides(thinking_mode="enabled", thinking_budget_tokens=4096),
                ),
            ),
        ),
    )
    base_settings = Settings(llm_base_url="http://base", llm_api_key="k", llm_model="m")

    # Fast target -> NO_THINKING in extra_body
    inv_fast = resolve_target_invocation(config, resolve_model_target(config, "fast"), base_settings)
    assert inv_fast is not None
    assert inv_fast.generation.extra_body == NO_THINKING

    # Reasoning target -> thinking budget in extra_body
    inv_reasoning = resolve_target_invocation(config, resolve_model_target(config, "reasoning"), base_settings)
    assert inv_reasoning is not None
    assert inv_reasoning.generation.extra_body == {"thinking": {"budget_tokens": 4096}}

    # Switching back to fast -> NO_THINKING
    inv_fast_again = resolve_target_invocation(config, resolve_model_target(config, "fast"), base_settings)
    assert inv_fast_again is not None
    assert inv_fast_again.generation.extra_body == NO_THINKING


def test_resolve_model_invocation_inherits_endpoint_rate_limit(tmp_path):
    events_path = tmp_path / "events.jsonl"
    events_path.write_text("", encoding="utf-8")
    config = OperatorConfig(
        llm=LLMPolicy(
            endpoints=(
                EndpointCatalogEntry(
                    id="rate-limited-ep",
                    base_url="http://rl:8000/v1",
                    rate_limit=EndpointRateLimitPolicy(min_interval_s=2.5, requests_per_minute=30),
                ),
            ),
            targets=(
                TargetCatalogEntry(
                    id="my-target",
                    endpoint="rate-limited-ep",
                    model="test-m",
                ),
            ),
        ),
    )
    base_settings = Settings()

    # Target-based invocation inherits endpoint rate limit
    inv = resolve_model_invocation(
        working=[{"role": "user", "content": "hi"}],
        operator_config=replace(config, llm=replace(config.llm, target="my-target")),
        base_settings=base_settings,
        settings_sources={"model": "env", "endpoint": "env", "api_key": "env", "transport": "env"},
        policy=default_backend_policy(),
        events_path=events_path,
        project_messages=lambda w: w,
        selected_endpoint=lambda w: None,
        selected_model=lambda w: None,
        secret_resolver=lambda **kw: "k",
    )
    assert inv.endpoint_id == "rate-limited-ep"
    assert inv.rate_limit.min_interval_s == 2.5
    assert inv.rate_limit.requests_per_minute == 30

    # Direct endpoint selection without target also inherits rate limit
    inv_ep = resolve_model_invocation(
        working=[{"role": "user", "content": "hi"}],
        operator_config=config,
        base_settings=base_settings,
        settings_sources={"model": "env", "endpoint": "env", "api_key": "env", "transport": "env"},
        policy=default_backend_policy(),
        events_path=events_path,
        project_messages=lambda w: w,
        selected_endpoint=lambda w: "rate-limited-ep",
        selected_model=lambda w: None,
        secret_resolver=lambda **kw: "k",
    )
    assert inv_ep.endpoint_id == "rate-limited-ep"
    assert inv_ep.rate_limit.min_interval_s == 2.5
    assert inv_ep.rate_limit.requests_per_minute == 30


# ---------------------------------------------------------------------------
# 3. Client-Side Throttling & Pacing Logic
# ---------------------------------------------------------------------------

def test_endpoint_throttler_min_interval_pacing():
    EndpointThrottler.reset_all()
    throttler = EndpointThrottler.get("test-ep-interval")
    policy = EndpointRateLimitPolicy(min_interval_s=1.0)

    simulated_time = 100.0
    sleeps: list[float] = []

    def fake_time():
        return simulated_time

    def fake_sleep(dur):
        nonlocal simulated_time
        sleeps.append(dur)
        simulated_time += dur

    # First call: no wait
    w1 = throttler.acquire(policy, time_fn=fake_time, sleep_fn=fake_sleep)
    assert w1 == 0.0
    assert len(sleeps) == 0

    # Call 0.3s later: must wait 0.7s
    simulated_time += 0.3
    w2 = throttler.acquire(policy, time_fn=fake_time, sleep_fn=fake_sleep)
    assert pytest.approx(w2, 0.001) == 0.7
    assert len(sleeps) == 1
    assert pytest.approx(sleeps[0], 0.001) == 0.7

    # Call 1.5s later: already exceeded min_interval, no wait
    simulated_time += 1.5
    w3 = throttler.acquire(policy, time_fn=fake_time, sleep_fn=fake_sleep)
    assert w3 == 0.0
    assert len(sleeps) == 1


def test_endpoint_throttler_requests_per_minute_ceiling():
    EndpointThrottler.reset_all()
    throttler = EndpointThrottler.get("test-ep-rpm")
    policy = EndpointRateLimitPolicy(requests_per_minute=3)

    simulated_time = 1000.0
    sleeps: list[float] = []

    def fake_time():
        return simulated_time

    def fake_sleep(dur):
        nonlocal simulated_time
        sleeps.append(dur)
        simulated_time += dur

    # Issue 3 requests within 5 seconds
    for _ in range(3):
        w = throttler.acquire(policy, time_fn=fake_time, sleep_fn=fake_sleep)
        assert w == 0.0
        simulated_time += 1.0

    # 4th request at t=1003.0: 3 calls were made at 1000.0, 1001.0, 1002.0.
    # Must wait until 1000.0 + 60.0 = 1060.0, which is 57.0s.
    w4 = throttler.acquire(policy, time_fn=fake_time, sleep_fn=fake_sleep)
    assert pytest.approx(w4, 0.001) == 57.0
    assert len(sleeps) == 1
    assert pytest.approx(sleeps[0], 0.001) == 57.0


def test_endpoint_throttler_reset():
    EndpointThrottler.reset_all()
    t = EndpointThrottler.get("resettable")
    t.last_call_time = 100.0
    t.call_history.append(100.0)
    t.reset()
    assert t.last_call_time is None
    assert len(t.call_history) == 0


def test_client_side_pacing_in_bounded_step_multi_turn(monkeypatch, tmp_path):
    EndpointThrottler.reset_all()
    toas_dir = tmp_path / ".toas"
    toas_dir.mkdir(parents=True, exist_ok=True)
    session_file = toas_dir / "session.md"
    session_file.write_text("## TOAS:USER\n\nRun loop\n", encoding="utf-8")
    config_file = tmp_path / "toas.toml"
    config_file.write_text(
        '[llm]\n'
        'target = "paced-target"\n'
        '[[llm.endpoints]]\n'
        'id = "paced-ep"\n'
        'base_url = "http://paced:8000/v1"\n'
        'rate_limit = { min_interval_s = 1.0 }\n'
        '[[llm.targets]]\n'
        'id = "paced-target"\n'
        'endpoint = "paced-ep"\n'
        'model = "m1"\n'
        '[shell]\n'
        'allowed_commands = ["echo"]\n',
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    call_times: list[float] = []
    call_count = 0

    def fake_generate(messages, **kwargs):
        nonlocal call_count
        call_count += 1
        call_times.append(time.monotonic())
        if call_count == 1:
            content = "```yaml\n- tool_name: echo\n  args:\n    text: turn1\n```"
        else:
            content = "Done."
        return {
            "role": "assistant",
            "content": content,
            "response": {"content": content, "model": "m1"},
        }

    monkeypatch.setattr(sgr, "generate_assistant_message", fake_generate)

    # Mock time.sleep inside throttler to avoid real sleep delay while measuring intervals
    throttler_sleeps: list[float] = []
    orig_acquire = EndpointThrottler.acquire

    def tracking_acquire(self, policy, **kw):
        def recording_sleep(d):
            throttler_sleeps.append(d)
        return orig_acquire(self, policy, sleep_fn=recording_sleep)

    monkeypatch.setattr(EndpointThrottler, "acquire", tracking_acquire)

    outcome = cli.run_step(max_turns=3)
    assert outcome.completed is True
    assert call_count == 2
    # Turn 2 must have waited because turn 1 was called virtually immediately before it
    assert len(throttler_sleeps) >= 1
    assert throttler_sleeps[0] > 0.0
    assert throttler_sleeps[0] <= 1.0


def test_endpoint_throttler_history_purging():
    EndpointThrottler.reset_all()
    throttler = EndpointThrottler.get("purge-test")
    policy = EndpointRateLimitPolicy(requests_per_minute=2)

    simulated_time = 100.0
    sleeps: list[float] = []

    def fake_time():
        return simulated_time

    def fake_sleep(dur):
        nonlocal simulated_time
        sleeps.append(dur)
        simulated_time += dur

    throttler.acquire(policy, time_fn=fake_time, sleep_fn=fake_sleep)
    assert len(throttler.call_history) == 1

    # Advance beyond 60s
    simulated_time = 170.0
    # Next call purges the first call before checking ceiling (covers line 66)
    throttler.acquire(policy, time_fn=fake_time, sleep_fn=fake_sleep)
    assert len(throttler.call_history) == 1

    # Second call within window
    simulated_time = 180.0
    throttler.acquire(policy, time_fn=fake_time, sleep_fn=fake_sleep)
    assert len(throttler.call_history) == 2

    # Third call within window triggers wait; after sleep, old calls purge (covers line 78)
    simulated_time = 185.0
    throttler.acquire(policy, time_fn=fake_time, sleep_fn=fake_sleep)
    assert len(sleeps) == 1


# ---------------------------------------------------------------------------
# 4. Interactive Configuration & Inspection Surface (/config)
# ---------------------------------------------------------------------------

def test_config_target_set_and_show():
    config = OperatorConfig(
        generation=GenerationPolicy(thinking_mode="disabled", max_tokens=1000),
        llm=LLMPolicy(
            endpoints=(
                EndpointCatalogEntry(
                    id="local",
                    base_url="http://localhost:8000/v1",
                    generation=TargetGenerationOverrides(transport_mode="chat_messages"),
                    rate_limit=EndpointRateLimitPolicy(min_interval_s=0.5, requests_per_minute=60),
                ),
            ),
            targets=(
                TargetCatalogEntry(
                    id="my-target",
                    endpoint="local",
                    model="model-a",
                ),
            ),
        ),
    )
    ctx = _make_context(config)
    step_mod = MagicMock()
    step_mod.flatten_config = lambda c: {}

    # 1. Update target with /config target <id> set ...
    res = _handle_config_command(
        ["target", "my-target", "set", "generation.thinking_budget_tokens", "4096"],
        step_mod=step_mod,
        context=ctx,
    )
    assert len(res) == 1
    assert "updated model target my-target.generation.thinking_budget_tokens" in res[0]["content"]
    assert res[0]["config_update"] == {
        "llm": {"targets": {"my-target": {"generation": {"thinking_budget_tokens": 4096}}}}
    }

    # 2. Update target with alternative syntax: /config target set <id> ...
    res_alt = _handle_config_command(
        ["target", "set", "my-target", "generation.max_tokens", "2048"],
        step_mod=step_mod,
        context=ctx,
    )
    assert len(res_alt) == 1
    assert "updated model target my-target.generation.max_tokens" in res_alt[0]["content"]

    # 3. Inspect target with /config show target <id>
    # Simulate config with the override applied
    updated_target = TargetCatalogEntry(
        id="my-target",
        endpoint="local",
        model="model-a",
        generation=TargetGenerationOverrides(thinking_budget_tokens=4096, max_tokens=2048),
    )
    ctx_updated = _make_context(replace(config, llm=replace(config.llm, targets=(updated_target,))))

    show_res = _handle_config_command(["show", "target", "my-target"], step_mod=step_mod, context=ctx_updated)
    assert len(show_res) == 1
    content = show_res[0]["content"]
    assert "target: my-target" in content
    assert "endpoint: local (http://localhost:8000/v1)" in content
    assert "thinking budget: 4096" in content
    assert "max tokens: 2048" in content
    assert "transport: chat_messages" in content  # inherited from endpoint
    assert "min interval: 0.5s" in content        # inherited from endpoint
    assert "requests per minute: 60" in content   # inherited from endpoint

    # 4. Unknown target raises ValueError
    with pytest.raises(ValueError, match="unknown model target: non-existent"):
        _handle_config_command(["show", "target", "non-existent"], step_mod=step_mod, context=ctx)


def test_config_endpoint_set_generation_and_rate_limit():
    config = OperatorConfig(
        llm=LLMPolicy(
            endpoints=(
                EndpointCatalogEntry(id="vllm", base_url="http://localhost:8000/v1"),
            ),
        ),
    )
    ctx = _make_context(config)
    step_mod = MagicMock()

    # 1. /config endpoint <id> set generation.transport_mode <mode>
    r1 = _handle_config_command(
        ["endpoint", "vllm", "set", "generation.transport_mode", "single_user_blob"],
        step_mod=step_mod,
        context=ctx,
    )
    assert "updated endpoint vllm.generation.transport_mode" in r1[0]["content"]
    assert r1[0]["config_update"]["llm"]["endpoints"][0]["generation"]["transport_mode"] == "single_user_blob"

    # 2. /config endpoint <id> set rate_limit.min_interval_s <seconds>
    r2 = _handle_config_command(
        ["endpoint", "vllm", "set", "rate_limit.min_interval_s", "1.5"],
        step_mod=step_mod,
        context=ctx,
    )
    assert "updated endpoint vllm.rate_limit.min_interval_s" in r2[0]["content"]
    assert r2[0]["config_update"]["llm"]["endpoints"][0]["rate_limit"]["min_interval_s"] == 1.5

    # 3. /config endpoint <id> set rate_limit.requests_per_minute <rpm>
    r3 = _handle_config_command(
        ["endpoint", "vllm", "set", "rate_limit.requests_per_minute", "120"],
        step_mod=step_mod,
        context=ctx,
    )
    assert "updated endpoint vllm.rate_limit.requests_per_minute" in r3[0]["content"]
    assert r3[0]["config_update"]["llm"]["endpoints"][0]["rate_limit"]["requests_per_minute"] == 120

    # 4. Alternative syntax: /config endpoint set <id>.<field> <val>
    r4 = _handle_config_command(
        ["endpoint", "set", "vllm.rate_limit.min_interval_s", "2.0"],
        step_mod=step_mod,
        context=ctx,
    )
    assert "updated endpoint vllm.rate_limit.min_interval_s" in r4[0]["content"]
    assert r4[0]["config_update"]["llm"]["endpoints"][0]["rate_limit"]["min_interval_s"] == 2.0


def test_endpoint_and_target_toml_roundtrip(tmp_path):
    p = tmp_path / "toas.toml"
    p.write_text(
        '[llm]\n'
        'target = "t1"\n'
        '[[llm.endpoints]]\n'
        'id = "ep-test"\n'
        'base_url = "http://test:8080/v1"\n'
        'generation = { thinking_mode = "enabled", transport_mode = "single_user_blob" }\n'
        'rate_limit = { min_interval_s = 1.25, requests_per_minute = 45 }\n'
        '[[llm.targets]]\n'
        'id = "t1"\n'
        'endpoint = "ep-test"\n'
        'model = "model-1"\n'
        'generation = { thinking_budget_tokens = 2048 }\n',
        encoding="utf-8",
    )
    cfg = config_from_file(p)
    assert len(cfg.llm.endpoints) == 1
    ep = cfg.llm.endpoints[0]
    assert ep.id == "ep-test"
    assert ep.generation.thinking_mode == "enabled"
    assert ep.generation.transport_mode == "single_user_blob"
    assert ep.rate_limit.min_interval_s == 1.25
    assert ep.rate_limit.requests_per_minute == 45

    assert len(cfg.llm.targets) == 1
    t = cfg.llm.targets[0]
    assert t.id == "t1"
    assert t.generation.thinking_budget_tokens == 2048

    # Serialize back and confirm toml serialization contains the structures
    toml_str = serialize_operator_config_toml(cfg)
    assert 'min_interval_s = 1.25' in toml_str
    assert 'requests_per_minute = 45' in toml_str
    assert 'thinking_budget_tokens = 2048' in toml_str


def test_endpoint_set_validation_errors():
    config = OperatorConfig(
        llm=LLMPolicy(
            endpoints=(
                EndpointCatalogEntry(id="ep1", base_url="http://ep1:8000/v1"),
            ),
        ),
    )
    ctx = _make_context(config)
    step_mod = MagicMock()

    # thinking_budget_tokens validation
    res_tb = _handle_config_command(["endpoint", "set", "ep1", "generation.thinking_budget_tokens", "100"], step_mod=step_mod, context=ctx)
    assert res_tb[0]["config_update"]["llm"]["endpoints"][0]["generation"]["thinking_budget_tokens"] == 100
    with pytest.raises(ValueError, match="generation.thinking_budget_tokens: expected int"):
        _handle_config_command(["endpoint", "ep1", "set", "generation.thinking_budget_tokens", "bad"], step_mod=step_mod, context=ctx)
    with pytest.raises(ValueError, match="generation.thinking_budget_tokens: expected >= 0"):
        _handle_config_command(["endpoint", "ep1", "set", "generation.thinking_budget_tokens", "-1"], step_mod=step_mod, context=ctx)

    # retry_delay_s validation
    res_rd = _handle_config_command(["endpoint", "ep1", "set", "generation.retry_delay_s", "0.5"], step_mod=step_mod, context=ctx)
    assert res_rd[0]["config_update"]["llm"]["endpoints"][0]["generation"]["retry_delay_s"] == 0.5
    with pytest.raises(ValueError, match="generation.retry_delay_s: expected float"):
        _handle_config_command(["endpoint", "ep1", "set", "generation.retry_delay_s", "bad"], step_mod=step_mod, context=ctx)
    with pytest.raises(ValueError, match="generation.retry_delay_s: expected >= 0"):
        _handle_config_command(["endpoint", "ep1", "set", "generation.retry_delay_s", "-0.5"], step_mod=step_mod, context=ctx)

    # avoid_terms
    res_avoid = _handle_config_command(["endpoint", "ep1", "set", "generation.avoid_terms", "foo, bar"], step_mod=step_mod, context=ctx)
    assert res_avoid[0]["config_update"]["llm"]["endpoints"][0]["generation"]["avoid_terms"] == ["foo", "bar"]

    # min_interval_s validation
    with pytest.raises(ValueError, match="rate_limit.min_interval_s: expected float"):
        _handle_config_command(["endpoint", "ep1", "set", "rate_limit.min_interval_s", "bad"], step_mod=step_mod, context=ctx)
    with pytest.raises(ValueError, match="rate_limit.min_interval_s: expected >= 0"):
        _handle_config_command(["endpoint", "ep1", "set", "rate_limit.min_interval_s", "-1.0"], step_mod=step_mod, context=ctx)

    # requests_per_minute validation
    with pytest.raises(ValueError, match="rate_limit.requests_per_minute: expected int"):
        _handle_config_command(["endpoint", "ep1", "set", "rate_limit.requests_per_minute", "bad"], step_mod=step_mod, context=ctx)
    with pytest.raises(ValueError, match="rate_limit.requests_per_minute: expected > 0"):
        _handle_config_command(["endpoint", "ep1", "set", "rate_limit.requests_per_minute", "0"], step_mod=step_mod, context=ctx)
    with pytest.raises(ValueError, match="rate_limit.requests_per_minute: expected > 0"):
        _handle_config_command(["endpoint", "ep1", "set", "rate_limit.requests_per_minute", "-5"], step_mod=step_mod, context=ctx)

    # requests_per_minute unset / none
    res_none = _handle_config_command(["endpoint", "ep1", "set", "rate_limit.requests_per_minute", "none"], step_mod=step_mod, context=ctx)
    assert res_none[0]["config_update"]["llm"]["endpoints"][0]["rate_limit"]["requests_per_minute"] is None

    # unknown field
    with pytest.raises(ValueError, match="endpoint field must be one of"):
        _handle_config_command(["endpoint", "ep1", "set", "unknown_field", "val"], step_mod=step_mod, context=ctx)

    # unknown endpoint id
    with pytest.raises(ValueError, match="unknown endpoint id: nonexistent"):
        _handle_config_command(["endpoint", "nonexistent", "set", "rate_limit.min_interval_s", "1.0"], step_mod=step_mod, context=ctx)

    # invalid usages
    with pytest.raises(ValueError, match="usage: /config endpoint"):
        _handle_config_command(["endpoint", "ep1", "set", "rate_limit.min_interval_s"], step_mod=step_mod, context=ctx)
    with pytest.raises(ValueError, match="usage: /config endpoint"):
        _handle_config_command(["endpoint", "set", "bad_target_no_dot", "1.0"], step_mod=step_mod, context=ctx)


def test_endpoint_declaration_update():
    from toas.runtime.operator_config_endpoint_ops import endpoint_declaration_update

    config = OperatorConfig(
        llm=LLMPolicy(
            endpoints=(
                EndpointCatalogEntry(id="ep1", base_url="http://ep1:8000/v1"),
            ),
        ),
    )
    up1 = endpoint_declaration_update(["endpoint", "ep1", "set", "rate_limit.min_interval_s", "2.5"], config=config)
    assert up1["llm"]["endpoints"][0]["rate_limit"]["min_interval_s"] == 2.5

    up2 = endpoint_declaration_update(["endpoint", "set", "ep1.rate_limit.min_interval_s", "3.0"], config=config)
    assert up2["llm"]["endpoints"][0]["rate_limit"]["min_interval_s"] == 3.0


def test_config_target_show_and_set_variants_and_errors():
    config = OperatorConfig(
        generation=GenerationPolicy(thinking_mode="disabled", max_tokens=1000),
        llm=LLMPolicy(
            endpoints=(
                EndpointCatalogEntry(
                    id="local",
                    base_url="http://localhost:8000/v1",
                    generation=TargetGenerationOverrides(transport_mode="chat_messages"),
                    rate_limit=EndpointRateLimitPolicy(min_interval_s=0.5, requests_per_minute=60),
                ),
            ),
            targets=(
                TargetCatalogEntry(
                    id="my-target",
                    endpoint="local",
                    model="model-a",
                    tags=("tag1", "tag2"),
                    notes="important target notes",
                ),
            ),
        ),
    )
    ctx = _make_context(config)
    step_mod = MagicMock()

    # 1. /config target <id> show
    r1 = _handle_config_command(["target", "my-target", "show"], step_mod=step_mod, context=ctx)
    assert "target: my-target" in r1[0]["content"]
    assert "tags: tag1, tag2" in r1[0]["content"]
    assert "notes: important target notes" in r1[0]["content"]

    # 2. /config target show <id>
    r2 = _handle_config_command(["target", "show", "my-target"], step_mod=step_mod, context=ctx)
    assert "target: my-target" in r2[0]["content"]

    # 3. /config target <id> (shorthand target inspection)
    r3 = _handle_config_command(["target", "my-target"], step_mod=step_mod, context=ctx)
    assert "target: my-target" in r3[0]["content"]

    # 4. /config show target (no target id -> render list)
    r4 = _handle_config_command(["show", "target"], step_mod=step_mod, context=ctx)
    assert "- my-target:" in r4[0]["content"]

    # 5. /config target show with missing target id
    with pytest.raises(ValueError, match="usage: /config target show NAME"):
        _handle_config_command(["target", "show"], step_mod=step_mod, context=ctx)

    # 6. /config target <id> set with invalid args
    with pytest.raises(ValueError, match="usage: /config target <NAME> set FIELD VALUE"):
        _handle_config_command(["target", "my-target", "set", "generation.max_tokens"], step_mod=step_mod, context=ctx)

    # 7. /config target <id> set on unknown target
    with pytest.raises(ValueError, match="unknown model target: missing"):
        _handle_config_command(["target", "missing", "set", "generation.max_tokens", "100"], step_mod=step_mod, context=ctx)


def test_config_overrides_endpoint_coercions():
    from toas.config import apply_overrides

    base_cfg = OperatorConfig()

    # Pass pre-instantiated classes
    overrides_obj = {
        "llm": {
            "endpoints": [
                EndpointCatalogEntry(
                    id="ep-obj",
                    base_url="http://ep-obj:8000/v1",
                    generation=TargetGenerationOverrides(thinking_mode="disabled"),
                    rate_limit=EndpointRateLimitPolicy(min_interval_s=1.0),
                ),
            ]
        }
    }
    cfg1 = apply_overrides(base_cfg, overrides_obj)
    assert cfg1.llm.endpoints[0].id == "ep-obj"
    assert cfg1.llm.endpoints[0].rate_limit.min_interval_s == 1.0

    # Pass dict with invalid string for min_interval and requests_per_minute, and avoid_terms list
    overrides_dict = {
        "llm": {
            "endpoints": [
                {
                    "id": "ep-dict",
                    "base_url": "http://ep-dict:8000/v1",
                    "generation": {
                        "avoid_terms": ["term1", "term2"],
                    },
                    "rate_limit": {
                        "min_interval_s": "not-a-float",
                        "requests_per_minute": "not-an-int",
                    },
                }
            ]
        }
    }
    cfg2 = apply_overrides(base_cfg, overrides_dict)
    assert cfg2.llm.endpoints[0].id == "ep-dict"
    assert cfg2.llm.endpoints[0].rate_limit.min_interval_s == 0.0
    assert cfg2.llm.endpoints[0].rate_limit.requests_per_minute is None
    assert cfg2.llm.endpoints[0].generation.avoid_terms == ("term1", "term2")

    # Non-dict fallback
    overrides_non_dict = {
        "llm": {
            "endpoints": [
                {
                    "id": "bad-ep",
                    "base_url": "http://bad-ep:8000/v1",
                    "generation": "not-a-dict",
                    "rate_limit": 12345,
                }
            ]
        }
    }
    cfg3 = apply_overrides(base_cfg, overrides_non_dict)
    assert cfg3.llm.endpoints[0].id == "bad-ep"
    assert cfg3.llm.endpoints[0].generation.thinking_mode is None
    assert cfg3.llm.endpoints[0].rate_limit.min_interval_s == 0.0


