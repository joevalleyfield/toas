## TOAS:USER

/config set llm.model gemma4
## RESULT

extraction.yaml_position = tail
extraction.loose_command_fallback = True
extraction.user_shell = True
extraction.operator_command = True
extraction.intent_arbitration = in_order
extraction.shell_staging = auto
extraction.projection_shape = auto
generation.thinking_mode = disabled
generation.avoid_terms = ('tool', 'tool-call', 'function', 'function-call')
generation.max_retries = 0
generation.retry_delay_s = 1.0
generation.transport_mode = chat_messages
llm.base_url = 
llm.model = gemma4
llm.api_key_source = env
llm.api_key_ref = TOAS_LLM_API_KEY
llm.models = ()
llm.backends = ()
runtime.context_budget_mode = balanced
runtime.streaming_mode = enabled
runtime.async_runs = enabled
runtime.cancellation_mode = enabled
runtime.thinking_stream_mode = disabled
runtime.prompt_progress_mode = disabled
shell.allowed_commands = ('echo', 'pwd', 'ls', 'cat', 'head', 'tail', 'wc', 'rg', 'find', 'sed', 'awk')
capability_advertisement.profile = core
capability_advertisement.hidden_tools = ()
backend_startup.thinking_budget_tokens = 0
backend.mode = external
backend.managed_local = {'command': (), 'cwd': '', 'env': (), 'health_url': '', 'health_timeout_s': 15.0}

Updated llm.model for this session.
Persist in project defaults by editing toas.toml.
Revert in-session with: /config set llm.model 


## TOAS:USER

/prompt dynamic/capabilities/overview_v1
## RESULT

Capabilities available in this TOAS session:
- advertisement profile: `core`
- I can inspect and shape transcript/history state, including selected head, jump binding, transcript projection, LLM-input inspection, and rebuild.
- I can use explicit prompt-library material that you choose to surface.
- I can use local action blocks instead of provider-native tool protocols when needed.
- I can use these local tools:
- `read_file`: read UTF-8 files inside the workspace (required args: path)
- `search`: search workspace text with rg (required args: query)
- `replace_block`: replace a block of text in a workspace file (required args: path, search_block, replacement_block)
- `apply_patch`: apply structured multi-file patches with strict context matching (required args: patch)
- `shell`: run bounded shell commands inside the workspace (required args: argv)
- `shell_script`: run bounded shell scripts inside the workspace (required args: script)
- `capability_help`: capability_help (required args: none)
Callable shape:
- aliases accepted: `operation`/`tool_name`, `arguments`/`args`/`params`, `intent`/`intention`
- use single operation by default
- use an operation list only for tightly coupled work (for example, coherent multi-file edits)
Multi-op example:
```yaml
- operation: replace_block
  arguments:
    path: src/a.py
    search_block: OLD_A
    replace_block: NEW_A
- operation: replace_block
  arguments:
    path: src/b.py
    search_block: OLD_B
    replace_block: NEW_B
```
`read_file` example:
```yaml
- operation: read_file
  arguments:
    path: src/toas/step.py
```
`search` example:
```yaml
- operation: search
  arguments:
    query: TODO
    path: .
```
`replace_block` example:
```yaml
- operation: replace_block
  arguments:
    path: src/app.py
    search_block: old
    replacement_block: new
    match_mode: default
```
`apply_patch` example:
```yaml
- operation: apply_patch
  arguments:
    patch: |
      *** Begin Patch
      *** Update File: src/app.py
      @@
      -old
      +new
      *** End Patch
```
`shell` example:
```yaml
- operation: shell
  arguments:
    argv: ["pwd"]
```
`shell_script` example:
```yaml
- operation: shell_script
  arguments:
    script: |
      find tasks/open -maxdepth 1 -type f | head -20
```
`capability_help` example:
```yaml
- operation: capability_help
  arguments: {}
```
Important limits:
- shell/shell_script are workspace-bounded and limited to timeout_s <= 30; allowed commands: awk, cat, echo, find, head, ls, pwd, rg, sed, tail, wc.
- I only have the capabilities explicitly available in this runtime; I should not imply hidden tools or provider-native tool access.
- For awkward backends, neutral action language is safer than `tool`, `tool-call`, `function`, `function-call`.


## TOAS:USER

/help tools
## RESULT

tools:
- apply_patch (args: patch)
- capability_help (args: none)
  optional args: topic
- code_survey (args: none)
  optional args: path, top_n
  defaults: path=src, top_n=20
- echo (args: text)
- echo_block (args: block)
- get_structure (args: path)
- procedure (args: name)
  optional args: arguments, dry_run
  defaults: arguments={}, dry_run=false
- read_file (args: path)
- replace_block (args: path, search_block, replacement_block)
- replace_range (args: path, start_line, end_line, replacement_block)
- search (args: query)
  optional args: path, limit, regex
  defaults: path=., limit=20, regex=false
- shell (args: argv)
  optional args: cwd, timeout_s, env
  defaults: cwd=., timeout_s=5
  allowed commands: awk, cat, echo, find, head, ls, pwd, rg, sed, tail, wc
  workspace-bounded, timeout_s <= 30
- shell_script (args: script)
  optional args: cwd, timeout_s, env
  defaults: cwd=., timeout_s=5
- write_file (args: path, content)
callable aliases: operation/tool_name, arguments/args/params, intent/intention
use a single operation by default; use a YAML list for tightly coupled multi-file updates


## TOAS:USER

Respond in exactly one of these shapes:
1) prose only
2) prose then YAML operations
3) YAML operations only
Never put explanatory prose inside operation argument payloads.
Task: implement /help config support in this TOAS repo, compact output, mention /config values <key>.
## TOAS:ASSISTANT

To implement `/help config` support, I will first investigate the existing help mechanism and the configuration loading logic to determine where the command routing and the configuration display logic should reside.

```yaml
- operation: search
  arguments:
    query: "/help"
- operation: search
  arguments:
    query: "config"
```

