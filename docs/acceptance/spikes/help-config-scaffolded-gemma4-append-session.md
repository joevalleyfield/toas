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

/prompt dynamic/capabilities/repo-work_v1
## RESULT

For repo and local-runtime work in this session, you can rely on these capabilities:
- `read_file` for reading workspace files (`arguments.path`).
- `search` for searching workspace text (`arguments.query`, optional `arguments.path`).
- `shell` for bounded workspace-local commands (`arguments.argv` list[str], not `command`).
- `shell_script` for bounded multiline/pipeline shell text (`arguments.script`).
- `replace_block` for targeted text replacements (`arguments.path`, `arguments.search_block`, `arguments.replacement_block`).
- `apply_patch` for structured multi-file edits (`arguments.patch`); strict context matching, no silent relocation on mismatch.
- `capability_help` for compact on-demand tool/policy detail by topic or tool name (`arguments.topic`).
- if argument shape is uncertain before first callable action, run `capability_help` first (for example topic `shell`).
- transcript/history inspection through transcript projection, LLM-input projection, and history/head controls.
When asking for actions, prefer local action blocks or neutral operation language rather than provider-native tool wording.


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

Implement /help config support in this TOAS repository. Keep help output compact, include usage guidance, and mention /config values <key>. Return callable operations only.
## TOAS:ASSISTANT

<|tool_call>call:code_survey{path=".",top_n=10}<tool_call|>

