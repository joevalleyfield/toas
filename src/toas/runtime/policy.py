from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path

from ..config import OperatorConfig
from ..llm import Settings
from ..secrets import resolve_secret
from ..shell_grants import normalize_shell_grants


@dataclass(frozen=True)
class ResolvedModelInvocationSettings:
    settings: Settings
    sources: dict[str, str]


@dataclass(frozen=True)
class ResolvedShellGrants:
    effective: tuple[str, ...]
    configured: tuple[str, ...]
    sources: dict[str, set[str]]
    session_added: tuple[str, ...]
    session_removed: tuple[str, ...]


@dataclass(frozen=True)
class ResolvedBackendStartupConfig:
    mode: str
    command: tuple[str, ...]
    cwd: str
    env: dict[str, str]
    health_url: str
    health_timeout_s: float
    fingerprint: str


class PolicyResolver:
    """Consolidated policy, authority, and config precedence resolver."""

    @staticmethod
    def has_nested_key(nested: dict, dotted_key: str) -> bool:
        current: object = nested
        for part in dotted_key.split("."):
            if not isinstance(current, dict) or part not in current:
                return False
            current = current[part]
        return True

    def resolve_settings(
        self,
        config: OperatorConfig,
        *,
        session_overrides: dict | None = None,
        runtime_secrets: dict[str, str] | None = None,
        environ: dict[str, str] | None = None,
    ) -> ResolvedModelInvocationSettings:
        orig_environ = os.environ
        if environ is not None:
            os.environ = dict(environ)
        try:
            base = Settings.from_env()
        finally:
            if environ is not None:
                os.environ = orig_environ
        
        session_overrides = session_overrides or {}
        secrets = runtime_secrets or {}

        llm_provider = config.llm.provider.strip() or base.llm_provider
        if self.has_nested_key(session_overrides, "llm.provider"):
            provider_source = "session_override"
        elif config.llm.provider.strip():
            provider_source = "config_file"
        else:
            provider_source = "env_or_default"

        llm_base_url = config.llm.base_url.strip()
        if self.has_nested_key(session_overrides, "llm.base_url"):
            endpoint_source = "session_override"
        elif config.llm.base_url.strip():
            endpoint_source = "config_file"
        else:
            endpoint_source = "env_or_default"

        if not llm_base_url:
            if llm_provider == "gemini-rest" and not os.getenv("TOAS_LLM_BASE_URL"):
                llm_base_url = "https://generativelanguage.googleapis.com"
            else:
                llm_base_url = base.llm_base_url

        llm_model = config.llm.model.strip() or base.llm_model
        if self.has_nested_key(session_overrides, "llm.model"):
            model_source = "session_override"
        elif config.llm.model.strip():
            model_source = "config_file"
        else:
            model_source = "env_or_default"

        if "llm_api_key" in secrets:
            llm_api_key = secrets["llm_api_key"]
            api_key_source = "runtime_secret"
        else:
            orig_environ = os.environ
            if environ is not None:
                os.environ = dict(environ)
            try:
                llm_api_key = resolve_secret(
                    source=config.llm.api_key_source,
                    ref=config.llm.api_key_ref,
                    default=base.llm_api_key,
                )
            finally:
                if environ is not None:
                    os.environ = orig_environ
            api_key_source = f"{config.llm.api_key_source}:{config.llm.api_key_ref}"

        transport_mode = config.generation.transport_mode
        if self.has_nested_key(session_overrides, "generation.transport_mode"):
            transport_source = "session_override"
        elif config.generation.transport_mode != "chat_messages":
            transport_source = "config_file"
        else:
            transport_source = "default"

        stream_mode = "enabled" if config.runtime.streaming_mode == "enabled" else "disabled"
        if self.has_nested_key(session_overrides, "runtime.streaming_mode"):
            stream_source = "session_override"
        elif config.runtime.streaming_mode != "enabled":
            stream_source = "config_file"
        else:
            stream_source = "default"

        settings = Settings(
            llm_base_url=llm_base_url,
            llm_api_key=llm_api_key,
            llm_model=llm_model,
            llm_trace=base.llm_trace,
            llm_transport_mode=transport_mode,
            llm_stream_mode=stream_mode,
            llm_provider=llm_provider,
        )
        return ResolvedModelInvocationSettings(
            settings=settings,
            sources={
                "endpoint": endpoint_source,
                "model": model_source,
                "api_key": api_key_source,
                "transport": transport_source,
                "stream": stream_source,
                "provider": provider_source,
            },
        )

    def resolve_stream_flags(
        self,
        config: OperatorConfig,
        environ: dict[str, str] | None = None,
    ) -> tuple[bool, bool]:
        env_map = environ if environ is not None else dict(os.environ)
        env_thinking = env_map.get("TOAS_STREAM_THINKING", "").strip().lower()
        env_progress = env_map.get("TOAS_STREAM_PROMPT_PROGRESS", "").strip().lower()
        env_truthy = {"1", "true", "yes", "on"}
        env_falsy = {"0", "false", "no", "off"}

        thinking_flag = config.runtime.thinking_stream_mode == "enabled"
        progress_flag = config.runtime.prompt_progress_mode == "enabled"

        if env_thinking in env_truthy:
            thinking_flag = True
        elif env_thinking in env_falsy:
            thinking_flag = False

        if env_progress in env_truthy:
            progress_flag = True
        elif env_progress in env_falsy:
            progress_flag = False

        return thinking_flag, progress_flag

    def resolve_stdout_stream(
        self,
        config: OperatorConfig,
        environ: dict[str, str] | None = None,
        env_modifiers: dict[str, str | None] | None = None,
    ) -> tuple[bool, str]:
        default_enabled = OperatorConfig().runtime.streaming_mode == "enabled"
        configured_enabled = config.runtime.streaming_mode == "enabled"
        env_map = environ if environ is not None else dict(os.environ)
        env_raw = env_map.get("TOAS_STREAM_STDOUT", "").strip().lower()
        env_enabled = env_raw in {"1", "true", "yes", "on"}
        env_disabled = env_raw in {"0", "false", "no", "off"}

        if configured_enabled != default_enabled:
            enabled = configured_enabled
            source = "config"
        elif env_enabled:
            enabled = True
            source = "env"
        elif env_disabled:
            enabled = False
            source = "env"
        else:
            enabled = default_enabled
            source = "default"

        if env_modifiers and "TOAS_STREAM_STDOUT" in env_modifiers:
            value = env_modifiers.get("TOAS_STREAM_STDOUT")
            if value is not None:
                raw = str(value).strip().lower()
                if raw in {"1", "true", "yes", "on"}:
                    return True, "transcript_env"
                if raw in {"0", "false", "no", "off"}:
                    return False, "transcript_env"
        return enabled, source

    def resolve_shell_grants(
        self,
        config: OperatorConfig,
        events: list[dict],
        shell_default_allowed: tuple[str, ...] = (),
    ) -> ResolvedShellGrants:
        from ..graph import active_shell_scope_grants

        configured = normalize_shell_grants(
            config.shell.allowed_commands if config.shell.allowed_commands else shell_default_allowed
        )
        allowed = set(configured)
        sources: dict[str, set[str]] = {grant: {"defaults"} for grant in configured}
        scope_state = active_shell_scope_grants(events)
        order = ("global", "user", "workspace", "head", "session", "transient")
        for scope in order:
            state = scope_state.get(scope, {"added": set(), "removed": set()})
            for grant in state["removed"]:
                allowed.discard(grant)
                if grant in sources:
                    sources[grant].add(scope)
            for grant in state["added"]:
                allowed.add(grant)
                sources.setdefault(grant, set()).add(scope)
        session_added = tuple(sorted(scope_state.get("session", {}).get("added", set())))
        session_removed = tuple(sorted(scope_state.get("session", {}).get("removed", set())))
        return ResolvedShellGrants(
            effective=tuple(sorted(allowed)),
            configured=tuple(sorted(configured)),
            sources=sources,
            session_added=session_added,
            session_removed=session_removed,
        )

    def resolve_backend_startup(
        self,
        config: OperatorConfig,
        cwd: Path,
    ) -> ResolvedBackendStartupConfig:
        mode = config.backend.mode
        managed = config.backend.managed_local
        command = tuple(managed.command)
        cwd_str = managed.cwd or str(cwd)
        env = dict(managed.env)
        health_url = managed.health_url
        health_timeout_s = managed.health_timeout_s

        fingerprint_data = {
            "mode": mode,
            "command": list(command),
            "cwd": cwd_str,
            "env": sorted(env.items()),
            "health_url": health_url,
            "health_timeout_s": health_timeout_s,
        }
        serialized = json.dumps(fingerprint_data, sort_keys=True)
        fingerprint = hashlib.sha256(serialized.encode("utf-8")).hexdigest()

        return ResolvedBackendStartupConfig(
            mode=mode,
            command=command,
            cwd=cwd_str,
            env=env,
            health_url=health_url,
            health_timeout_s=health_timeout_s,
            fingerprint=fingerprint,
        )
