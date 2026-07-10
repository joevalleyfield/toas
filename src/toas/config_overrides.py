from dataclasses import asdict

from .shell_grants import normalize_shell_grants


def deep_merge(base: dict, override: dict) -> dict:
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def apply_overrides(config, nested: dict, *, classes) -> object:
    """Merge a nested override dict onto an existing config, returning a new instance."""
    merged = deep_merge(asdict(config), nested)
    extraction = classes["ExtractionPolicy"](**merged.get("extraction", {}))
    generation_values = merged.get("generation", {})
    if "avoid_terms" in generation_values and isinstance(generation_values["avoid_terms"], list):
        generation_values = dict(generation_values)
        generation_values["avoid_terms"] = tuple(generation_values["avoid_terms"])
    generation = classes["GenerationPolicy"](**generation_values)

    llm_values = dict(merged.get("llm", {}))
    model_entries: list[object] = []
    raw_models = llm_values.get("models", [])
    if isinstance(raw_models, tuple):
        raw_models = list(raw_models)
    if isinstance(raw_models, list):
        for item in raw_models:
            if isinstance(item, classes["ModelCatalogEntry"]):
                model_entries.append(item)
                continue
            if not isinstance(item, dict):
                continue
            model_id = str(item.get("id", "")).strip()
            if not model_id:
                continue
            label = str(item.get("label", "")).strip()
            notes = str(item.get("notes", "")).strip()
            tags_raw = item.get("tags", ())
            if isinstance(tags_raw, (list, tuple)):
                tags = tuple(str(tag).strip() for tag in tags_raw if str(tag).strip())
            else:
                tags = ()
            model_entries.append(classes["ModelCatalogEntry"](id=model_id, label=label, tags=tags, notes=notes))
    llm_values["models"] = tuple(model_entries)

    backend_entries: list[object] = []
    raw_backends = llm_values.get("backends", [])
    if isinstance(raw_backends, tuple):
        raw_backends = list(raw_backends)
    if isinstance(raw_backends, list):
        for item in raw_backends:
            if isinstance(item, classes["BackendCatalogEntry"]):
                backend_entries.append(item)
                continue
            if not isinstance(item, dict):
                continue
            backend_id = str(item.get("id", "")).strip()
            base_url = str(item.get("base_url", "")).strip()
            if not backend_id or not base_url:
                continue
            model = str(item.get("model", "")).strip()
            models_raw = item.get("models", ())
            if isinstance(models_raw, (list, tuple)):
                models = tuple(str(model_id).strip() for model_id in models_raw if str(model_id).strip())
            else:
                models = ()
            api_key_source = str(item.get("api_key_source", "env")).strip().lower() or "env"
            if api_key_source not in {"env", "keyring"}:
                api_key_source = "env"
            api_key_ref = str(item.get("api_key_ref", "TOAS_LLM_API_KEY")).strip() or "TOAS_LLM_API_KEY"
            tags_raw = item.get("tags", ())
            if isinstance(tags_raw, (list, tuple)):
                tags = tuple(str(tag).strip() for tag in tags_raw if str(tag).strip())
            else:
                tags = ()
            notes = str(item.get("notes", "")).strip()
            backend_entries.append(
                classes["BackendCatalogEntry"](
                    id=backend_id,
                    base_url=base_url,
                    model=model,
                    models=models,
                    api_key_source=api_key_source,
                    api_key_ref=api_key_ref,
                    tags=tags,
                    notes=notes,
                )
            )
    llm_values["backends"] = tuple(backend_entries)
    llm = classes["LLMPolicy"](**llm_values)
    runtime = classes["RuntimePolicy"](**merged.get("runtime", {}))

    shell_values = merged.get("shell", {})
    if isinstance(shell_values.get("allowed_commands"), list):
        shell_values = dict(shell_values)
        shell_values["allowed_commands"] = normalize_shell_grants(
            tuple(str(item).strip() for item in shell_values["allowed_commands"] if str(item).strip())
        )
    shell = classes["ShellPolicy"](**shell_values)

    capability_advertisement = classes["CapabilityAdvertisementPolicy"](**merged.get("capability_advertisement", {}))
    session = classes["SessionPolicy"](**merged.get("session", {}))
    tool_writes = classes["ToolWritePolicy"](**merged.get("tool_writes", {}))
    backend_startup = classes["BackendStartupPolicy"](**merged.get("backend_startup", {}))
    backend_values = dict(merged.get("backend", {}))
    managed_values = dict(backend_values.get("managed_local", {}))

    command_raw = managed_values.get("command", ())
    if isinstance(command_raw, list):
        managed_values["command"] = tuple(str(part) for part in command_raw if str(part))

    env_raw = managed_values.get("env", ())
    env_pairs: list[tuple[str, str]] = []
    if isinstance(env_raw, dict):
        for key, value in env_raw.items():
            key_s = str(key).strip()
            if key_s:
                env_pairs.append((key_s, str(value)))
    elif isinstance(env_raw, list):
        for item in env_raw:
            if isinstance(item, (tuple, list)) and len(item) == 2:
                key_s = str(item[0]).strip()
                if key_s:
                    env_pairs.append((key_s, str(item[1])))
    managed_values["env"] = tuple(env_pairs)

    managed_local = classes["BackendManagedLocalPolicy"](**managed_values)
    backend_values["managed_local"] = managed_local
    backend = classes["BackendPolicy"](**backend_values)
    diagnostics = classes["DiagnosticsPolicy"](**merged.get("diagnostics", {}))
    return classes["OperatorConfig"](
        extraction=extraction,
        generation=generation,
        llm=llm,
        runtime=runtime,
        shell=shell,
        capability_advertisement=capability_advertisement,
        session=session,
        tool_writes=tool_writes,
        backend_startup=backend_startup,
        backend=backend,
        diagnostics=diagnostics,
    )
