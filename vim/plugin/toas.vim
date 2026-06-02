if exists('g:loaded_toas_plugin')
  finish
endif
let g:loaded_toas_plugin = 1

let s:toas_channel = v:null
let s:toas_host_channel = v:null
let s:toas_host_rx_buffer = ''
let s:toas_host_start_cmd = []
let s:toas_host_last_exit = v:null
let s:toas_host_stderr_tail = []
let s:toas_host_start_time = v:null
let s:toas_host_launch_transport = ''
let g:toas_last_step_transport = ''
let g:toas_last_error = ''
let g:toas_last_rpc_raw_len = -1
let g:toas_last_rpc_stdout_len = -1
let g:toas_active_run_id = ''
let g:toas_last_run_status = ''
let g:toas_last_step_lane = ''
let g:toas_last_step_fallback_reason = ''
let g:toas_last_step_timing = {}
let s:toas_watch_offset = {}
let s:toas_watch_seq = {}
let s:toas_run_text = {}
let s:toas_run_progress = {}
let s:toas_run_status = {}
let s:toas_run_reasoning_open = {}
let s:toas_run_seen_event_keys = {}
let s:toas_run_last_content_lane = {}
let s:toas_run_error_summary = {}
let s:toas_run_stream_policy = {}
let s:toas_run_buffers = {}
let s:toas_run_timers = {}
let s:toas_run_data_pumps = {}
let s:toas_run_metrics = {}
let s:toas_run_prompt_progress_debug = {}
let s:toas_lane_health = {}
let s:toas_step_counter = 0
let s:toas_run_watch_ticks = {}
let s:toas_run_watch_interval = {}
let s:toas_watch_debug = {}
let s:toas_host_job = -1
let s:toas_run_phase_ms = {}
let s:toas_watch_empty_streak = {}
let s:toas_watch_pump = {}
let s:toas_run_pending_append = {}
let s:toas_run_last_rendered_text = {}
let s:toas_run_region_cache = {}
let s:toas_wire_log_buffer = []
let s:toas_wire_log_dir_ready = 0
let s:toas_wire_log_path = ''
let s:toas_wire_log_flush_every = 64
let s:toas_tick_log_every = 10
let s:toas_tick_log_state = {}
let s:toas_tick_edge_log_only = 1
let s:toas_tick_phase_edges_enabled = 0
if !exists('g:toas_step_nonblocking')
  let g:toas_step_nonblocking = 1
endif
if !exists('g:toas_notice_enabled')
  let g:toas_notice_enabled = 0
endif
if !exists('g:toas_step_lane_order')
  let g:toas_step_lane_order = ['default', 'warm', 'cold', 'synchronous']
endif
if !exists('g:toas_lane_failure_threshold')
  let g:toas_lane_failure_threshold = 2
endif
if !exists('g:toas_lane_cooldown_steps')
  let g:toas_lane_cooldown_steps = 3
endif
if !exists('g:toas_transport_mode')
  " Architecture-shift default: Vim's primary path is editor-owned local host.
  " RPC remains an explicit compatibility opt-back (`g:toas_transport_mode='rpc_local_backend'`).
  let g:toas_transport_mode = 'local_host'
endif
if !exists('g:toas_local_host_debug_single_lane')
  let g:toas_local_host_debug_single_lane = 1
endif
if !exists('g:toas_local_host_wire_log')
  let g:toas_local_host_wire_log = 1
endif
if !exists('g:toas_watch_max_frames_per_tick')
  let g:toas_watch_max_frames_per_tick = 512
endif
if !exists('g:toas_watch_decode_budget')
  let g:toas_watch_decode_budget = 512
endif
if !exists('g:toas_watch_pump_log_every')
  let g:toas_watch_pump_log_every = 10
endif
if !exists('g:toas_watch_apply_bytes_per_tick')
  let g:toas_watch_apply_bytes_per_tick = 16384
endif
if !exists('g:toas_watch_first_frame_timeout_ms')
  let g:toas_watch_first_frame_timeout_ms = 45000
endif
if !exists('g:toas_watch_inter_frame_timeout_ms')
  let g:toas_watch_inter_frame_timeout_ms = 15000
endif
if !exists('g:toas_watch_subscribe_timeout_s')
  let g:toas_watch_subscribe_timeout_s = 30.0
endif

function! s:toas_wire_log(msg) abort
  if !get(g:, 'toas_local_host_wire_log', 0)
    return
  endif
  if s:toas_wire_log_path ==# ''
    let s:toas_wire_log_path = s:toas_workdir() . '/.toas/host-stdio-vim.log'
  endif
  if !s:toas_wire_log_dir_ready
    call mkdir(fnamemodify(s:toas_wire_log_path, ':h'), 'p')
    let s:toas_wire_log_dir_ready = 1
  endif
  let l:epoch_ms = float2nr(reltimefloat(reltime()) * 1000.0)
  let l:iso = strftime('%Y-%m-%dT%H:%M:%S', localtime()) . '.' . printf('%03d', l:epoch_ms % 1000)
  call add(s:toas_wire_log_buffer, l:iso . ' ms=' . l:epoch_ms . ' ' . a:msg)
  if len(s:toas_wire_log_buffer) >= s:toas_wire_log_flush_every
    call s:toas_wire_log_flush()
  endif
endfunction

function! s:toas_wire_log_flush() abort
  if empty(s:toas_wire_log_buffer)
    return
  endif
  if s:toas_wire_log_path ==# ''
    let s:toas_wire_log_path = s:toas_workdir() . '/.toas/host-stdio-vim.log'
  endif
  if !s:toas_wire_log_dir_ready
    call mkdir(fnamemodify(s:toas_wire_log_path, ':h'), 'p')
    let s:toas_wire_log_dir_ready = 1
  endif
  call writefile(s:toas_wire_log_buffer, s:toas_wire_log_path, 'a')
  let s:toas_wire_log_buffer = []
endfunction

function! s:toas_tick_log_state_get(run_id) abort
  if !has_key(s:toas_tick_log_state, a:run_id)
    let s:toas_tick_log_state[a:run_id] = {'count': 0}
  endif
  return s:toas_tick_log_state[a:run_id]
endfunction

function! s:toas_tick_log_state_clear(run_id) abort
  if has_key(s:toas_tick_log_state, a:run_id)
    call remove(s:toas_tick_log_state, a:run_id)
  endif
endfunction

function! s:toas_tick_phase_edges_enabled() abort
  if exists('g:toas_tick_phase_edges_enabled')
    return get(g:, 'toas_tick_phase_edges_enabled', 0) ? 1 : 0
  endif
  return s:toas_tick_phase_edges_enabled ? 1 : 0
endfunction

function! s:toas_watch_pump_ensure_state(run_id) abort
  if !has_key(s:toas_watch_pump, a:run_id)
    let s:toas_watch_pump[a:run_id] = {
          \ 'phase': 'subscribe_send',
          \ 'request_id': '',
          \ 'last_activity_ms': float2nr(reltimefloat(reltime()) * 1000.0),
          \ 'last_status': 'running',
          \ 'last_push_complete': -1,
          \ 'subscribe_started_ms': 0,
          \ 'ticks_since_subscribe': 0,
          \ 'last_probe_ms': 0,
          \ 'frame_ordinal': 0,
          \ 'pump_tick': 0,
          \ 'bytes_rx': 0,
          \ 'frames_decoded': 0,
          \ 'frames_adapted': 0,
          \ 'bytes_applied': 0,
          \ 'seen_frame_keys': {},
          \ 'pending': [],
          \ 'ingress_lines': [],
          \ 'adapted_frames': [],
          \ }
  endif
  return s:toas_watch_pump[a:run_id]
endfunction

function! s:toas_prompt_progress_debug_note(run_id, text) abort
  if !has_key(s:toas_run_prompt_progress_debug, a:run_id)
    let s:toas_run_prompt_progress_debug[a:run_id] = {'count': 0, 'first': '', 'last': ''}
  endif
  let s:toas_run_prompt_progress_debug[a:run_id].count += 1
  if s:toas_run_prompt_progress_debug[a:run_id].first ==# ''
    let s:toas_run_prompt_progress_debug[a:run_id].first = a:text
  endif
  let s:toas_run_prompt_progress_debug[a:run_id].last = a:text
  call s:toas_wire_log('PROMPT_PROGRESS_RENDER run_id=' . a:run_id . ' count=' . s:toas_run_prompt_progress_debug[a:run_id].count . ' text=' . string(a:text))
endfunction

function! s:toas_watch_pump_collect_ingress(run_id, pump) abort
  if strlen(s:toas_host_rx_buffer) > 0
    if get(a:pump, 'bytes_rx', 0) == 0
      call s:toas_phase_mark(a:run_id, 'first_rx')
    endif
    let a:pump.bytes_rx = get(a:pump, 'bytes_rx', 0) + strlen(s:toas_host_rx_buffer)
    call s:toas_wire_log('HARVEST_RX run_id=' . a:run_id . ' bytes=' . strlen(s:toas_host_rx_buffer))
  endif

  let l:norm = substitute(s:toas_host_rx_buffer, "\%x00", '', 'g')
  let l:parts = split(l:norm, "\n", 1)
  if len(l:parts) <= 1
    if strlen(s:toas_host_rx_buffer) > 0
      call s:toas_wire_log('INGRESS_PARTIAL run_id=' . a:run_id . ' buffered=' . strlen(s:toas_host_rx_buffer))
    endif
    return 0
  endif

  let s:toas_host_rx_buffer = l:parts[-1]
  if !has_key(a:pump, 'ingress_lines') || type(a:pump.ingress_lines) != type([])
    let a:pump.ingress_lines = []
  endif
  for l:i in range(0, len(l:parts) - 2)
    let l:part = l:parts[l:i]
    if l:part !=# ''
      call add(a:pump.ingress_lines, l:part)
    endif
  endfor
  call s:toas_wire_log('INGRESS_LINES run_id=' . a:run_id . ' queued=' . len(a:pump.ingress_lines) . ' tail_len=' . strlen(s:toas_host_rx_buffer))
  return len(a:pump.ingress_lines)
endfunction

function! s:toas_watch_pump_decode_phase(run_id, pump) abort
  let l:decoded = []
  let l:decoded_seen = 0
  let l:decoded_before = get(a:pump, 'frames_decoded', 0)
  let l:decode_budget = max([1, get(g:, 'toas_watch_decode_budget', 256)])
  let l:decode_budget_ms = max([1, get(g:, 'toas_watch_decode_budget_ms', 12)])
  let l:decode_budget_start = reltime()
  let l:first_resp_id = ''
  if !has_key(a:pump, 'ingress_lines') || type(a:pump.ingress_lines) != type([])
    let a:pump.ingress_lines = []
  endif
  let l:remaining = []
  while !empty(a:pump.ingress_lines)
    if l:decoded_seen >= l:decode_budget || s:toas_ms_since(l:decode_budget_start) >= l:decode_budget_ms
      let l:remaining = copy(a:pump.ingress_lines)
      call s:toas_wire_log('HARVEST_DECODE_BUDGET run_id=' . a:run_id . ' processed=' . l:decoded_seen . ' budget=' . l:decode_budget . ' budget_ms=' . l:decode_budget_ms)
      break
    endif
    let l:part = remove(a:pump.ingress_lines, 0)
    if l:part ==# ''
      continue
    endif
    try
      let l:parsed = json_decode(l:part)
      if type(l:parsed) != type({})
        continue
      endif
      let l:decoded_seen += 1
      let a:pump.frames_decoded = get(a:pump, 'frames_decoded', 0) + 1
      if l:first_resp_id ==# ''
        let l:first_resp_id = string(get(l:parsed, 'request_id', ''))
      endif
      let l:resp_id = get(l:parsed, 'request_id', '')
      let l:payload = get(l:parsed, 'payload', {})
      let l:payload_run_id = get(l:payload, 'run_id', '')
      if l:payload_run_id ==# ''
        let l:single_event = get(l:payload, 'event', {})
        if type(l:single_event) == type({})
          let l:payload_run_id = get(l:single_event, 'run_id', '')
        endif
      endif
      if l:payload_run_id ==# ''
        let l:payload_events = get(l:payload, 'events', [])
        if type(l:payload_events) == type([]) && !empty(l:payload_events)
          let l:first_event = l:payload_events[0]
          if type(l:first_event) == type({})
            let l:payload_run_id = get(l:first_event, 'run_id', '')
          endif
        endif
      endif
      let l:kind = get(l:payload, 'kind', '')
      let l:active_request_id = get(a:pump, 'request_id', '')
      let l:matched_id = (l:active_request_id !=# '' && l:resp_id ==# l:active_request_id)
      let l:matched_run = (l:payload_run_id ==# a:run_id)
      " During subscribe window rotation, host frames may arrive with the prior request_id.
      " Keep push frames for the active watcher when run_id is omitted instead of dropping.
      let l:accept_orphan_push = (l:payload_run_id ==# '' && (l:kind ==# 'push_event' || l:kind ==# 'push_complete'))
      if !l:matched_id && !l:matched_run && !l:accept_orphan_push
        if l:kind ==# 'push_event' || l:kind ==# 'push_complete'
          call s:toas_wire_log(
                \ 'PUMP_DROP_STALE run_id=' . a:run_id
                \ . ' expected_request_id=' . string(l:active_request_id)
                \ . ' got_request_id=' . string(l:resp_id)
                \ . ' payload_run_id=' . string(l:payload_run_id)
                \ . ' kind=' . string(l:kind)
                \ )
        endif
        continue
      endif
      if l:accept_orphan_push && !l:matched_id && !l:matched_run
        call s:toas_wire_log(
              \ 'PUMP_ACCEPT_ORPHAN_PUSH run_id=' . a:run_id
              \ . ' expected_request_id=' . string(l:active_request_id)
              \ . ' got_request_id=' . string(l:resp_id)
              \ . ' kind=' . string(l:kind)
              \ )
      endif
      let a:pump.frame_ordinal = get(a:pump, 'frame_ordinal', 0) + 1
      let l:frame_key = l:resp_id . '#' . string(a:pump.frame_ordinal)
      call add(l:decoded, {'parsed': l:parsed, 'frame_key': l:frame_key})
    catch
    endtry
  endwhile
  let a:pump.ingress_lines = l:remaining
  if l:decoded_seen > 0
    if l:decoded_before == 0
      call s:toas_phase_mark(a:run_id, 'first_decode')
    endif
    let g:toas_last_watch_decode_ms = s:toas_ms_since(l:decode_budget_start)
    call s:toas_wire_log('RECV_BATCH run_id=' . a:run_id . ' decoded=' . l:decoded_seen . ' first_request_id=' . l:first_resp_id)
  endif
  if !empty(l:decoded)
    if !has_key(a:pump, 'pending') || type(a:pump.pending) != type([])
      let a:pump.pending = []
    endif
    call extend(a:pump.pending, l:decoded)
    call s:toas_wire_log('HARVEST_DECODE run_id=' . a:run_id . ' frames=' . len(l:decoded) . ' pending=' . len(a:pump.pending) . ' ord=' . get(a:pump, 'frame_ordinal', 0))
  endif
endfunction

function! s:toas_watch_pump_adapt_phase(run_id, pump, now_ms) abort
  let l:adapt_start = reltime()
  let l:max_frames = max([1, get(g:, 'toas_watch_max_frames_per_tick', 256)])
  let l:frame_budget_ms = max([1, get(g:, 'toas_watch_frame_budget_ms', 12)])
  let l:frame_budget_start = reltime()
  let l:frames = []
  let l:done = v:false
  while !empty(a:pump.pending) && len(l:frames) < l:max_frames && !l:done
    if s:toas_ms_since(l:frame_budget_start) >= l:frame_budget_ms
      break
    endif
    let l:item = remove(a:pump.pending, 0)
    if type(l:item) == type({})
      let l:parsed = get(l:item, 'parsed', {})
      let l:frame_key = get(l:item, 'frame_key', '')
    else
      let l:parsed = l:item
      let l:frame_key = ''
    endif
    if l:frame_key !=# '' && has_key(a:pump.seen_frame_keys, l:frame_key)
      call s:toas_wire_log('FRAME_DUP_DROP run_id=' . a:run_id . ' key=' . l:frame_key)
      continue
    endif
    if l:frame_key !=# ''
      let a:pump.seen_frame_keys[l:frame_key] = 1
    endif
    let l:adapted = s:toas_watch_pump_frame_to_response(a:run_id, l:parsed, a:pump, a:now_ms)
    if empty(l:adapted)
      let l:pl = get(l:parsed, 'payload', {})
      call s:toas_wire_log(
            \ 'ADAPT_EMPTY run_id=' . a:run_id
            \ . ' request_id=' . string(get(l:parsed, 'request_id', ''))
            \ . ' kind=' . string(get(l:pl, 'kind', ''))
            \ . ' payload_run_id=' . string(get(l:pl, 'run_id', ''))
            \ )
      continue
    endif
    call add(l:frames, l:adapted)
    let a:pump.frames_adapted = get(a:pump, 'frames_adapted', 0) + 1
    let l:status = s:toas_normalize_run_status(get(get(l:adapted, 'payload', {}), 'status', 'running'))
    if s:toas_is_terminal_status(l:status)
      let l:done = v:true
    endif
  endwhile
  let g:toas_last_watch_adapt_ms = s:toas_ms_since(l:adapt_start)
  return l:frames
endfunction

function! s:toas_phase_mark(run_id, key) abort
  if type(a:run_id) != type('') || a:run_id ==# ''
    return
  endif
  if !has_key(s:toas_run_phase_ms, a:run_id)
    let s:toas_run_phase_ms[a:run_id] = {}
  endif
  let s:toas_run_phase_ms[a:run_id][a:key] = float2nr(reltimefloat(reltime()) * 1000.0)
endfunction

function! s:toas_phase_summary(run_id) abort
  if !has_key(s:toas_run_phase_ms, a:run_id)
    return ''
  endif
  let l:p = s:toas_run_phase_ms[a:run_id]
  let l:s = get(l:p, 'step_start', -1)
  let l:m = get(l:p, 'marker', -1)
  let l:send = get(l:p, 'send', -1)
  let l:ack = get(l:p, 'ack', -1)
  let l:tick = get(l:p, 'first_tick', -1)
  let l:sub = get(l:p, 'subscribe_send', -1)
  let l:rx = get(l:p, 'first_rx', -1)
  let l:dec = get(l:p, 'first_decode', -1)
  let l:ren = get(l:p, 'first_render', -1)
  let l:parts = []
  if l:s >= 0 && l:m >= 0 | call add(l:parts, 'start_to_marker=' . (l:m - l:s) . 'ms') | endif
  if l:m >= 0 && l:send >= 0 | call add(l:parts, 'marker_to_send=' . (l:send - l:m) . 'ms') | endif
  if l:send >= 0 && l:ack >= 0 | call add(l:parts, 'send_to_ack=' . (l:ack - l:send) . 'ms') | endif
  if l:ack >= 0 && l:tick >= 0 | call add(l:parts, 'ack_to_first_tick=' . (l:tick - l:ack) . 'ms') | endif
  if l:ack >= 0 && l:sub >= 0 | call add(l:parts, 'ack_to_sub_send=' . (l:sub - l:ack) . 'ms') | endif
  if l:sub >= 0 && l:rx >= 0 | call add(l:parts, 'sub_send_to_first_rx=' . (l:rx - l:sub) . 'ms') | endif
  if l:rx >= 0 && l:dec >= 0 | call add(l:parts, 'first_rx_to_first_decode=' . (l:dec - l:rx) . 'ms') | endif
  if l:dec >= 0 && l:ren >= 0 | call add(l:parts, 'first_decode_to_first_render=' . (l:ren - l:dec) . 'ms') | endif
  return join(l:parts, ' ')
endfunction

function! s:toas_notice(msg) abort
  if !get(g:, 'toas_notice_enabled', 0)
    return
  endif
  redraw
  echohl ModeMsg
  echon a:msg
  echohl None
endfunction

function! s:toas_normalize_workdir_root(path) abort
  if type(a:path) != type('') || a:path ==# ''
    return a:path
  endif
  let l:path = trim(fnamemodify(a:path, ':p'))
  let l:path = substitute(l:path, '[/\\]\+$', '', '')
  " Canonicalize any path that points inside .toas back to repo root.
  " We cut at the first `/.toas` segment to handle nested `.toas/.toas/...`.
  let l:toas_seg_idx = match(l:path, '[/\\]\.toas\([/\\]\|$\)')
  if l:toas_seg_idx >= 0
    let l:path = strpart(l:path, 0, l:toas_seg_idx)
    if l:path ==# ''
      return getcwd()
    endif
  endif
  let l:path = substitute(l:path, '[/\\]\+$', '', '')
  return l:path
endfunction

function! s:toas_workdir() abort
  if exists('g:toas_workdir') && type(g:toas_workdir) == type('') && g:toas_workdir !=# ''
    let l:raw = g:toas_workdir
    let l:resolved = s:toas_normalize_workdir_root(l:raw)
    " Self-heal polluted session state (e.g. `.../.toas`) so subsequent
    " logs and payload construction are unambiguous.
    if l:resolved !=# '' && l:resolved !=# l:raw
      let g:toas_workdir = l:resolved
    endif
    if has('win32') || has('win64')
      return substitute(l:resolved, '^\/\([a-zA-Z]\)\/', '\1:\/', '')
    endif
    return l:resolved
  endif

  let l:start = expand('%:p:h')
  if l:start ==# ''
    let l:start = getcwd()
  endif
  let l:start = s:toas_normalize_workdir_root(l:start)
  let l:probe = finddir('.toas', l:start . ';')
  if l:probe !=# ''
    let l:resolved = s:toas_normalize_workdir_root(fnamemodify(l:probe, ':p:h'))
    if has('win32') || has('win64')
      return substitute(l:resolved, '^\/\([a-zA-Z]\)\/', '\1:\/', '')
    endif
    return l:resolved
  endif
  let l:cfg = findfile('toas.toml', l:start . ';')
  if l:cfg !=# ''
    let l:resolved = s:toas_normalize_workdir_root(fnamemodify(l:cfg, ':p:h'))
    if has('win32') || has('win64')
      return substitute(l:resolved, '^\/\([a-zA-Z]\)\/', '\1:\/', '')
    endif
    return l:resolved
  endif

  let l:fallback = s:toas_normalize_workdir_root(getcwd())
  if has('win32') || has('win64')
    return substitute(l:fallback, '^\/\([a-zA-Z]\)\/', '\1:\/', '')
  endif
  return l:fallback
endfunction

function! s:toas_socket_path() abort
  if exists('g:toas_socket_path')
    return g:toas_socket_path
  endif
  return s:toas_workdir() . '/.toas/toas.sock'
endfunction

function! s:toas_vim_port_path() abort
  if exists('g:toas_vim_port_path')
    return g:toas_vim_port_path
  endif
  let l:candidates = [
        \ s:toas_workdir() . '/.toas/toas.vim-port',
        \ s:toas_workdir() . '/.toas.vim-port',
        \ getcwd() . '/.toas/toas.vim-port',
        \ getcwd() . '/.toas.vim-port',
        \ ]
  for l:path in l:candidates
    if filereadable(l:path)
      return l:path
    endif
  endfor
  let l:found = findfile('.toas.vim-port', expand('%:p:h') . ';')
  if l:found !=# ''
    return fnamemodify(l:found, ':p')
  endif
  return l:candidates[0]
endfunction

function! s:toas_request_id() abort
  return printf('%d-%d', localtime(), float2nr(reltimefloat(reltime()) * 1000000.0))
endfunction

function! s:toas_channel_open() abort
  if !exists('*ch_open') || !exists('*ch_status') || !exists('*ch_sendraw') || !exists('*ch_readraw')
    return 0
  endif

  try
    if s:toas_channel isnot v:null && ch_status(s:toas_channel) ==# 'open'
      return 1
    endif
  catch
    let s:toas_channel = v:null
  endtry

  if has('win32') || has('win64') || has('win32unix')
    let l:port_file = s:toas_vim_port_path()
    if !filereadable(l:port_file)
      return 0
    endif
    let l:port = trim(readfile(l:port_file)[0])
    if l:port ==# ''
      return 0
    endif
    let l:addr = '127.0.0.1:' . l:port
  else
    let l:addr = 'unix:' . s:toas_socket_path()
  endif
  let g:toas_last_addr = l:addr

  try
    let s:toas_channel = ch_open(l:addr, {'mode': 'raw'})
    if s:toas_channel is v:null
      let g:toas_last_open_status = 'null'
      return 0
    endif
    let g:toas_last_open_status = ch_status(s:toas_channel)
    return g:toas_last_open_status ==# 'open'
  catch
    let s:toas_channel = v:null
    let g:toas_last_open_status = 'exception: ' . v:exception
    return 0
  endtry
endfunction

function! s:toas_step_rpc() abort
  let l:resp = s:toas_request('step', {'workdir': s:toas_workdir()}, 5.0)
  return get(get(l:resp, 'payload', {}), 'stdout', '')
endfunction

function! s:toas_step_rpc_async_collect() abort
  let l:start = s:toas_request('step_async_cold', {'workdir': s:toas_workdir()}, 5.0)
  let l:start_payload = get(l:start, 'payload', {})
  let l:run_id = get(l:start_payload, 'run_id', '')
  if l:run_id ==# ''
    throw 'missing run_id in step_async response'
  endif

  let g:toas_active_run_id = l:run_id
  let g:toas_last_run_status = get(l:start_payload, 'status', '')
  let s:toas_watch_offset[l:run_id] = 0
  let s:toas_watch_seq[l:run_id] = 0

  let l:accum = ''
  while 1
    let l:watch_payload = {
          \ 'workdir': s:toas_workdir(),
          \ 'run_id': l:run_id,
          \ 'offset': get(s:toas_watch_offset, l:run_id, 0),
          \ 'since_seq': get(s:toas_watch_seq, l:run_id, 0),
          \ }
    let l:watch = s:toas_request('watch', l:watch_payload, 5.0)
    let l:data = get(l:watch, 'payload', {})
    let l:chunk = get(l:data, 'chunk', '')
    if l:chunk !=# ''
      let l:accum .= l:chunk
    endif
    let s:toas_watch_offset[l:run_id] = get(l:data, 'next_offset', get(s:toas_watch_offset, l:run_id, 0))
    let s:toas_watch_seq[l:run_id] = get(l:data, 'next_seq', get(s:toas_watch_seq, l:run_id, 0))
    let l:status = get(l:data, 'status', '')
    let g:toas_last_run_status = l:status
    if l:status ==# 'succeeded' || l:status ==# 'failed' || l:status ==# 'cancelled'
      break
    endif
    sleep 100m
  endwhile
  return l:accum
endfunction

function! s:toas_run_marker_start(run_id) abort
  return '## TOAS:RUN ' . a:run_id
endfunction

function! s:toas_run_marker_end(run_id) abort
  return '## /TOAS:RUN ' . a:run_id
endfunction

function! s:toas_find_run_region(bufnr, run_id) abort
  let l:start_marker = s:toas_run_marker_start(a:run_id)
  let l:end_marker = s:toas_run_marker_end(a:run_id)
  let l:lines = getbufline(a:bufnr, 1, '$')
  let l:line_count = len(l:lines)
  if l:line_count == 0
    return []
  endif
  " Fast path: bounded search around the previous hit for this run.
  if has_key(s:toas_run_region_cache, a:run_id)
    let l:cached = s:toas_run_region_cache[a:run_id]
    let l:cached_start = get(l:cached, 'start', -1)
    let l:cached_end = get(l:cached, 'end', -1)
    if l:cached_start >= 1 && l:cached_end >= l:cached_start
      let l:window = max([20, (l:cached_end - l:cached_start + 1) * 4])
      let l:from = max([1, l:cached_start - l:window])
      let l:to = min([l:line_count, l:cached_end + l:window])
      let l:i = l:from - 1
      while l:i <= l:to - 1
        if l:lines[l:i] ==# l:start_marker
          let l:j = l:i + 1
          while l:j <= l:to - 1
            if l:lines[l:j] ==# l:end_marker
              let l:start_hit = l:i + 1
              let l:end_hit = l:j + 1
              let s:toas_run_region_cache[a:run_id] = {'start': l:start_hit, 'end': l:end_hit}
              return [l:start_hit, l:end_hit]
            endif
            let l:j += 1
          endwhile
        endif
        let l:i += 1
      endwhile
    endif
  endif
  let l:start = -1
  let l:end = -1
  let l:i = 0
  while l:i < len(l:lines)
    if l:lines[l:i] ==# l:start_marker
      let l:start = l:i + 1
      let l:j = l:i + 1
      while l:j < len(l:lines)
        if l:lines[l:j] ==# l:end_marker
          let l:end = l:j + 1
          let s:toas_run_region_cache[a:run_id] = {'start': l:start, 'end': l:end}
          return [l:start, l:end]
        endif
        let l:j += 1
      endwhile
      return []
    endif
    let l:i += 1
  endwhile
  return []
endfunction

function! s:toas_render_run_lines(run_id, status, text, progress) abort
  let l:lines = [s:toas_run_marker_start(a:run_id), 'status: ' . a:status]
  if has_key(s:toas_run_stream_policy, a:run_id)
    let l:policy = s:toas_run_stream_policy[a:run_id]
    if type(l:policy) == type({})
      let l:thinking = get(l:policy, 'thinking', v:false) ? 'on' : 'off'
      let l:prompt = get(l:policy, 'prompt_progress', v:false) ? 'on' : 'off'
      call add(l:lines, 'stream: thinking=' . l:thinking . ' prompt_progress=' . l:prompt)
    endif
  endif
  if a:progress !=# ''
    call add(l:lines, 'progress: ' . a:progress)
  endif
  call add(l:lines, '')
  if a:text !=# ''
    let l:body = split(substitute(a:text, '\r', '', 'g'), "\n", 1)
    for l:line in l:body
      if l:line =~# '^prompt \d\+/\d\+'
        continue
      endif
      call add(l:lines, l:line)
    endfor
  endif
  call add(l:lines, s:toas_run_marker_end(a:run_id))
  return l:lines
endfunction

function! s:toas_extract_prompt_progress(text) abort
  if a:text ==# ''
    return ''
  endif
  let l:lines = split(substitute(a:text, '\r', '', 'g'), "\n", 1)
  if empty(l:lines)
    return ''
  endif
  let l:i = len(l:lines) - 1
  while l:i >= 0
    let l:line = l:lines[l:i]
    if l:line =~# '^prompt \d\+/\d\+'
      return l:line
    endif
    let l:i -= 1
  endwhile
  return ''
endfunction

function! s:toas_prompt_progress_enabled_for_run(run_id) abort
  if !has_key(s:toas_run_stream_policy, a:run_id)
    return 0
  endif
  let l:policy = s:toas_run_stream_policy[a:run_id]
  if type(l:policy) != type({})
    return 0
  endif
  return get(l:policy, 'prompt_progress', v:false) ? 1 : 0
endfunction

function! s:toas_normalize_run_status(status) abort
  if type(a:status) != type('')
    return ''
  endif
  let l:s = tolower(a:status)
  if l:s ==# 'completed'
    return 'succeeded'
  endif
  return l:s
endfunction

function! s:toas_is_terminal_status(status) abort
  let l:s = s:toas_normalize_run_status(a:status)
  return l:s ==# 'succeeded' || l:s ==# 'failed' || l:s ==# 'cancelled'
endfunction

function! s:toas_format_progress_event(payload) abort
  if type(a:payload) != type({})
    return ''
  endif
  let l:processed = get(a:payload, 'processed', -1)
  let l:total = get(a:payload, 'total', -1)
  if type(l:processed) != type(0) || type(l:total) != type(0) || l:processed < 0 || l:total <= 0
    return ''
  endif
  let l:pct = float2nr((l:processed * 100.0) / l:total)
  let l:text = printf('prompt %d/%d (%d%%)', l:processed, l:total, l:pct)
  let l:cache = get(a:payload, 'cache', v:null)
  if type(l:cache) == type(0) && l:cache >= 0
    let l:text .= printf(' | cache=%d', l:cache)
  endif
  let l:time_ms = get(a:payload, 'time_ms', v:null)
  if type(l:time_ms) == type(0) && l:time_ms >= 0
    let l:text .= printf(' | t=%dms', l:time_ms)
  endif
  return l:text
endfunction

function! s:toas_extract_text_from_event(event) abort
  if type(a:event) != type({})
    return ''
  endif
  let l:payload = get(a:event, 'payload', {})
  if type(l:payload) != type({})
    return ''
  endif
  let l:lane = get(a:event, 'lane', '')
  let l:phase = get(a:event, 'phase', '')
  if (l:lane ==# 'llm_answer' || l:lane ==# 'tool' || l:lane ==# 'llm_reasoning' || l:lane ==# 'projection') && l:phase ==# 'delta'
    let l:text = get(l:payload, 'text', '')
    if type(l:text) == type('') && l:text !=# ''
      return l:text
    endif
  endif
  let l:chunk = get(l:payload, 'chunk', '')
  if type(l:chunk) == type('') && l:chunk !=# ''
    return l:chunk
  endif
  let l:content = get(l:payload, 'content', '')
  if type(l:content) == type('') && l:content !=# ''
    return l:content
  endif
  let l:text2 = get(l:payload, 'text', '')
  if type(l:text2) == type('') && l:text2 !=# ''
    return l:text2
  endif
  return ''
endfunction

function! s:toas_thinking_open_marker() abort
  return "## TOAS:THINKING\n"
endfunction

function! s:toas_thinking_close_marker() abort
  return "\n## /TOAS:THINKING\n"
endfunction

function! s:toas_append_reasoning_close_if_open(run_id) abort
  if get(s:toas_run_reasoning_open, a:run_id, 0)
    let s:toas_run_reasoning_open[a:run_id] = 0
    return s:toas_thinking_close_marker()
  endif
  return ''
endfunction

function! s:toas_extract_renderable_event_text(run_id, event) abort
  if type(a:event) != type({})
    return ''
  endif
  let l:text = s:toas_extract_text_from_event(a:event)
  let l:lane = get(a:event, 'lane', '')
  let l:phase = get(a:event, 'phase', '')
  if l:text !=# ''
    if l:lane ==# 'llm_reasoning' && l:phase ==# 'delta'
      if !get(s:toas_run_reasoning_open, a:run_id, 0)
        let s:toas_run_reasoning_open[a:run_id] = 1
        return s:toas_thinking_open_marker() . l:text
      endif
      return l:text
    endif
    return s:toas_append_reasoning_close_if_open(a:run_id) . l:text
  endif
  let l:event_type = get(a:event, 'type', '')
  let l:payload = get(a:event, 'payload', {})
  let l:status = type(l:payload) == type({}) ? s:toas_normalize_run_status(get(l:payload, 'status', '')) : ''
  if (l:event_type ==# 'llm_done' || l:event_type ==# 'run_done' || l:event_type ==# 'tool_done') && s:toas_is_terminal_status(l:status)
    return s:toas_append_reasoning_close_if_open(a:run_id)
  endif
  return ''
endfunction

function! s:toas_collect_event_text(events) abort
  if type(a:events) != type([])
    return ''
  endif
  let l:accum = ''
  for l:event in a:events
    if type(l:event) != type({})
      continue
    endif
    let l:accum .= s:toas_extract_text_from_event(l:event)
  endfor
  return l:accum
endfunction

function! s:toas_apply_chunk_with_carriage(existing, chunk) abort
  if a:chunk ==# ''
    return a:existing
  endif

  let l:out = a:existing
  let l:parts = split(a:chunk, '\r', 1)
  if !empty(l:parts)
    let l:out .= remove(l:parts, 0)
  endif

  for l:part in l:parts
    let l:last_nl = strridx(l:out, "\n")
    if l:last_nl >= 0
      let l:out = strpart(l:out, 0, l:last_nl + 1)
    else
      let l:out = ''
    endif
    let l:out .= l:part
  endfor
  return l:out
endfunction

function! s:toas_render_run_body_lines(text) abort
  let l:text = substitute(a:text, '\r', '', 'g')
  if l:text =~# '^## RESULT\>' && l:text !~# '^## TOAS:\(SYSTEM\|USER\|ASSISTANT\)\>'
    let l:text = "## TOAS:USER\n\n" . l:text
  endif
  let l:lines = split(l:text, "\n", 1)
  if empty(l:lines)
    return ['']
  endif
  return l:lines
endfunction

function! s:toas_extract_final_projection(text) abort
  let l:lines = split(substitute(a:text, '\r', '', 'g'), "\n", 1)
  let l:start = -1
  let l:i = 0
  while l:i < len(l:lines)
    let l:line = l:lines[l:i]
    if l:line =~# '^## TOAS:\(SYSTEM\|USER\|ASSISTANT\)$' || l:line ==# '## RESULT'
      let l:start = l:i
      break
    endif
    let l:i += 1
  endwhile
  if l:start < 0
    return a:text
  endif
  return join(l:lines[l:start:], "\n")
endfunction

function! s:toas_ensure_projection_for_lane(text, lane) abort
  let l:text = substitute(a:text, '\r', '', 'g')
  if l:text =~# '^## TOAS:\(SYSTEM\|USER\|ASSISTANT\)\>'
    return l:text
  endif
  if l:text =~# '^## RESULT\>'
    return "## TOAS:USER\n\n" . l:text
  endif
  if a:lane ==# 'tool'
    return "## TOAS:USER\n\n## RESULT\n\n" . l:text
  endif
  return '## TOAS:ASSISTANT' . "\n" . l:text
endfunction

function! s:toas_compact_error_message(message) abort
  if type(a:message) != type('')
    return ''
  endif
  let l:text = substitute(a:message, '\r', '', 'g')
  for l:line in split(l:text, "\n", 1)
    let l:line = substitute(l:line, '^\s\+', '', '')
    let l:line = substitute(l:line, '\s\+$', '', '')
    if l:line !=# '' && l:line !~# '^Traceback '
      if strlen(l:line) > 300
        return strpart(l:line, 0, 300) . '...'
      endif
      return l:line
    endif
  endfor
  return ''
endfunction

function! s:toas_capture_error_event(run_id, event) abort
  if type(a:event) != type({})
    return
  endif
  let l:payload = get(a:event, 'payload', {})
  if type(l:payload) != type({})
    return
  endif
  let l:event_type = get(a:event, 'type', '')
  let l:status = tolower(get(l:payload, 'status', ''))
  let l:raw = ''
  if l:event_type ==# 'error'
    let l:raw = get(l:payload, 'message', '')
  elseif (l:status ==# 'failed' || l:status ==# 'cancelled') && has_key(l:payload, 'error')
    let l:raw = get(l:payload, 'error', '')
  endif
  let l:summary = s:toas_compact_error_message(l:raw)
  if l:summary !=# ''
    let s:toas_run_error_summary[a:run_id] = l:summary
  endif
endfunction

function! s:toas_replace_buffer_region(bufnr, start, end, lines) abort
  let l:restore_view = 0
  if bufnr('%') == a:bufnr
    let l:view = winsaveview()
    let l:restore_view = 1
  endif

  if exists('*deletebufline') && exists('*appendbufline')
    call deletebufline(a:bufnr, a:start, a:end)
    call appendbufline(a:bufnr, a:start - 1, a:lines)
    if l:restore_view
      call winrestview(l:view)
    endif
    return
  endif

  " Fallback path for older Vim builds lacking appendbufline/deletebufline.
  let l:orig = bufnr('%')
  let l:view = winsaveview()
  if l:orig != a:bufnr
    execute 'silent noautocmd keepalt buffer ' . a:bufnr
  endif
  execute a:start . ',' . a:end . 'delete _'
  call append(a:start - 1, a:lines)
  if l:orig != a:bufnr
    execute 'silent noautocmd keepalt buffer ' . l:orig
  endif
  if l:restore_view
    call winrestview(l:view)
  endif
endfunction

function! s:toas_replace_run_region(run_id, status, text, keep_markers) abort
  if !has_key(s:toas_run_buffers, a:run_id)
    return 0
  endif
  let l:bufnr = s:toas_run_buffers[a:run_id]
  if !bufexists(l:bufnr) || !bufloaded(l:bufnr)
    return 0
  endif
  let l:region = s:toas_find_run_region(l:bufnr, a:run_id)
  if empty(l:region)
    return 0
  endif
  let l:start = l:region[0]
  let l:end = l:region[1]
  if a:keep_markers
    let l:new_lines = s:toas_render_run_lines(a:run_id, a:status, a:text, get(s:toas_run_progress, a:run_id, ''))
  else
    let l:new_lines = s:toas_render_run_body_lines(a:text)
  endif
  let l:existing_lines = getbufline(l:bufnr, l:start, l:end)
  if l:existing_lines ==# l:new_lines
    let s:toas_run_last_rendered_text[a:run_id] = a:text
    return 0
  endif
  call s:toas_replace_buffer_region(l:bufnr, l:start, l:end, l:new_lines)
  let s:toas_run_last_rendered_text[a:run_id] = a:text
  return 1
endfunction

function! s:toas_append_run_region_chunk(run_id, status, chunk) abort
  if a:chunk ==# '' || !has_key(s:toas_run_buffers, a:run_id)
    return 0
  endif
  let l:bufnr = s:toas_run_buffers[a:run_id]
  if !bufexists(l:bufnr) || !bufloaded(l:bufnr)
    return 0
  endif
  let l:region = s:toas_find_run_region(l:bufnr, a:run_id)
  if empty(l:region)
    return 0
  endif
  let l:start = l:region[0]
  let l:end = l:region[1]
  let l:old_text = get(s:toas_run_last_rendered_text, a:run_id, '')
  let l:new_text = s:toas_apply_chunk_with_carriage(l:old_text, a:chunk)
  if l:new_text ==# l:old_text
    return 0
  endif
  let l:prefix = ['status: ' . a:status]
  if has_key(s:toas_run_stream_policy, a:run_id)
    let l:policy = s:toas_run_stream_policy[a:run_id]
    if type(l:policy) == type({})
      let l:thinking = get(l:policy, 'thinking', v:false) ? 'on' : 'off'
      let l:prompt = get(l:policy, 'prompt_progress', v:false) ? 'on' : 'off'
      call add(l:prefix, 'stream: thinking=' . l:thinking . ' prompt_progress=' . l:prompt)
    endif
  endif
  let l:progress = get(s:toas_run_progress, a:run_id, '')
  if l:progress !=# ''
    call add(l:prefix, 'progress: ' . l:progress)
  endif
  call add(l:prefix, '')
  let l:body = s:toas_render_run_body_lines(l:new_text)
  call s:toas_replace_buffer_region(l:bufnr, l:start + 1, l:end - 1, l:prefix + l:body)
  let s:toas_run_last_rendered_text[a:run_id] = l:new_text
  return 1
endfunction

function! s:toas_insert_run_region(run_id, status, insert_after) abort
  let l:bufnr = bufnr('%')
  let l:view = winsaveview()
  let l:lines = s:toas_render_run_lines(a:run_id, a:status, '', '')
  call append(a:insert_after, l:lines)
  call winrestview(l:view)
  let s:toas_run_buffers[a:run_id] = l:bufnr
  let s:toas_run_region_cache[a:run_id] = {'start': a:insert_after + 1, 'end': a:insert_after + len(l:lines)}
  let s:toas_run_status[a:run_id] = a:status
  let s:toas_run_progress[a:run_id] = ''
  return 1
endfunction

function! s:toas_remove_run_region(run_id) abort
  if !has_key(s:toas_run_buffers, a:run_id)
    return
  endif
  let l:bufnr = s:toas_run_buffers[a:run_id]
  if !bufexists(l:bufnr) || !bufloaded(l:bufnr)
    return
  endif
  let l:region = s:toas_find_run_region(l:bufnr, a:run_id)
  if empty(l:region)
    return
  endif
  call s:toas_replace_buffer_region(l:bufnr, l:region[0], l:region[1], [])
endfunction

function! s:toas_relabel_run_region(old_run_id, new_run_id, status) abort
  if !has_key(s:toas_run_buffers, a:old_run_id)
    return 0
  endif
  let l:bufnr = s:toas_run_buffers[a:old_run_id]
  if !bufexists(l:bufnr) || !bufloaded(l:bufnr)
    return 0
  endif
  let l:region = s:toas_find_run_region(l:bufnr, a:old_run_id)
  if empty(l:region)
    return 0
  endif
  let l:start = l:region[0]
  let l:end = l:region[1]
  let l:text = get(s:toas_run_text, a:old_run_id, '')
  let l:progress = get(s:toas_run_progress, a:old_run_id, '')
  let l:lines = s:toas_render_run_lines(a:new_run_id, a:status, l:text, l:progress)
  call s:toas_replace_buffer_region(l:bufnr, l:start, l:end, l:lines)
  return 1
endfunction

function! s:toas_stop_run_watcher(run_id) abort
  if has_key(s:toas_run_timers, a:run_id)
    call timer_stop(s:toas_run_timers[a:run_id])
    call remove(s:toas_run_timers, a:run_id)
  endif
  if has_key(s:toas_run_data_pumps, a:run_id)
    try
      call timer_stop(s:toas_run_data_pumps[a:run_id])
    catch
    endtry
    call remove(s:toas_run_data_pumps, a:run_id)
  endif
  if has_key(s:toas_run_watch_ticks, a:run_id)
    call remove(s:toas_run_watch_ticks, a:run_id)
  endif
  if has_key(s:toas_run_watch_interval, a:run_id)
    call remove(s:toas_run_watch_interval, a:run_id)
  endif
  if has_key(s:toas_watch_empty_streak, a:run_id)
    call remove(s:toas_watch_empty_streak, a:run_id)
  endif
  if has_key(s:toas_watch_pump, a:run_id)
    call remove(s:toas_watch_pump, a:run_id)
  endif
  if has_key(s:toas_run_seen_event_keys, a:run_id)
    call remove(s:toas_run_seen_event_keys, a:run_id)
  endif
  if has_key(s:toas_run_last_content_lane, a:run_id)
    call remove(s:toas_run_last_content_lane, a:run_id)
  endif
  if has_key(s:toas_run_error_summary, a:run_id)
    call remove(s:toas_run_error_summary, a:run_id)
  endif
  if has_key(s:toas_run_pending_append, a:run_id)
    call remove(s:toas_run_pending_append, a:run_id)
  endif
  if has_key(s:toas_run_last_rendered_text, a:run_id)
    call remove(s:toas_run_last_rendered_text, a:run_id)
  endif
  if has_key(s:toas_run_region_cache, a:run_id)
    call remove(s:toas_run_region_cache, a:run_id)
  endif
  call s:toas_tick_log_state_clear(a:run_id)
endfunction

function! s:toas_schedule_data_pump(run_id) abort
  if !exists('*timer_start')
    return
  endif
  if has_key(s:toas_run_data_pumps, a:run_id)
    return
  endif
  let s:toas_run_data_pumps[a:run_id] = timer_start(1, function('s:toas_run_data_pump_tick', [a:run_id]))
endfunction

function! s:toas_run_data_pump_tick(run_id, timer_id) abort
  if has_key(s:toas_run_data_pumps, a:run_id)
    call remove(s:toas_run_data_pumps, a:run_id)
  endif
  if !has_key(s:toas_run_timers, a:run_id)
    return
  endif
  if get(s:toas_run_status, a:run_id, 'running') !=# 'running'
    return
  endif
  " Reuse the existing watcher callback path so transport/presentation semantics stay unified.
  call s:toas_watch_tick(a:run_id, -1)
endfunction

function! s:toas_watch_pump_tick(run_id, payload) abort
  let g:toas_last_watch_decode_ms = 0
  let g:toas_last_watch_adapt_ms = 0
  let l:pump = s:toas_watch_pump_ensure_state(a:run_id)
  let l:now_ms = float2nr(reltimefloat(reltime()) * 1000.0)

  if l:pump.phase ==# 'subscribe_send'
    if exists('g:ToasTestLocalHostSubscribeFn') && type(g:ToasTestLocalHostSubscribeFn) == type(function('tr'))
      let l:test_frames = call(g:ToasTestLocalHostSubscribeFn, [a:run_id, 1.0])
      if type(l:test_frames) != type([])
        let l:test_frames = []
      endif
      if !has_key(l:pump, 'pending') || type(l:pump.pending) != type([])
        let l:pump.pending = []
      endif
      call extend(l:pump.pending, l:test_frames)
      let l:pump.phase = 'harvest'
      let l:pump.request_id = 'test-subscribe-' . a:run_id
      let l:pump.last_activity_ms = l:now_ms
      let l:pump.subscribe_started_ms = l:now_ms
      let l:pump.ticks_since_subscribe = 0
      let s:toas_watch_pump[a:run_id] = l:pump
      call s:toas_wire_log('SEND op=stream_subscribe request_id=' . l:pump.request_id . ' attempt=1 test_hook=1')
      return {}
    endif
    if !s:toas_host_ensure_started()
      throw 'local_host unavailable: host process not running'
    endif
    if s:toas_host_channel is v:null || ch_status(s:toas_host_channel) !=# 'open'
      throw 'local_host unavailable: host channel not open'
    endif
    let l:req = {
          \ 'protocol_version': 1,
          \ 'request_id': s:toas_request_id(),
          \ 'op': 'stream_subscribe',
          \ 'payload': {
          \   'run_id': a:run_id,
          \   'timeout_s': str2float(string(get(g:, 'toas_watch_subscribe_timeout_s', 30.0))),
          \   'offset': get(s:toas_watch_offset, a:run_id, 0),
          \   'since_seq': get(s:toas_watch_seq, a:run_id, 0),
          \ },
          \ }
    call s:toas_wire_log('SEND op=stream_subscribe request_id=' . l:req.request_id . ' attempt=1')
    call s:toas_phase_mark(a:run_id, 'subscribe_send')
    call ch_sendraw(s:toas_host_channel, json_encode(l:req) . "\n")
    let l:pump.phase = 'harvest'
    let l:pump.request_id = l:req.request_id
    let l:pump.last_activity_ms = l:now_ms
    let l:pump.subscribe_started_ms = l:now_ms
    let l:pump.ticks_since_subscribe = 0
    let s:toas_watch_pump[a:run_id] = l:pump
    return {}
  endif

  " harvest phase: strictly nonblocking drain of pushed frames
  let l:pump.pump_tick = get(l:pump, 'pump_tick', 0) + 1
  let l:pump.ticks_since_subscribe = get(l:pump, 'ticks_since_subscribe', 0) + 1
  if s:toas_host_channel is v:null || ch_status(s:toas_host_channel) !=# 'open'
    throw 'local_host unavailable: host channel not open'
  endif
  " Keep newline as the only frame boundary; NULs are transport noise on some Vim builds.
  " Important: always attempt ingress collect/decode first so high pending depth
  " cannot starve new stdio frames.
  call s:toas_watch_pump_collect_ingress(a:run_id, l:pump)
  let l:parts = get(l:pump, 'ingress_lines', [])
  if !empty(l:parts)
    let l:pump.no_progress_ticks = 0
    let l:pump.ingress_lines = l:parts
    call s:toas_watch_pump_decode_phase(a:run_id, l:pump)
    call s:toas_wire_log('PUMP_DECODE_PROGRESS run_id=' . a:run_id . ' pending=' . (has_key(l:pump, 'pending') ? len(l:pump.pending) : 0) . ' ingress_left=' . len(get(l:pump, 'ingress_lines', [])))
  endif

  if has_key(l:pump, 'pending') && type(l:pump.pending) == type([]) && !empty(l:pump.pending)
    let l:frames = s:toas_watch_pump_adapt_phase(a:run_id, l:pump, l:now_ms)
    let s:toas_watch_pump[a:run_id] = l:pump
    return s:toas_merge_watch_like_frames(a:run_id, l:frames)
  endif

  if empty(l:parts)
    let l:pump.no_progress_ticks = get(l:pump, 'no_progress_ticks', 0) + 1
    call s:toas_wire_log('HARVEST_IDLE_NOFRAMES run_id=' . a:run_id . ' no_progress_ticks=' . l:pump.no_progress_ticks . ' rx_buffer=' . strlen(s:toas_host_rx_buffer))
  endif
  if get(g:, 'toas_watch_pump_log_every', 0) > 0
    let l:log_every = max([1, get(g:, 'toas_watch_pump_log_every', 10)])
    if (get(l:pump, 'pump_tick', 0) % l:log_every) == 0
      call s:toas_wire_log(
            \ 'PUMP_COUNTER run_id=' . a:run_id
            \ . ' tick=' . get(l:pump, 'pump_tick', 0)
            \ . ' bytes_rx=' . get(l:pump, 'bytes_rx', 0)
            \ . ' frames_decoded=' . get(l:pump, 'frames_decoded', 0)
            \ . ' frames_adapted=' . get(l:pump, 'frames_adapted', 0)
            \ . ' bytes_applied=' . get(l:pump, 'bytes_applied', 0)
            \ . ' pending=' . (has_key(l:pump, 'pending') ? len(l:pump.pending) : 0))
    endif
  endif
  let l:first_frame_timeout_ms = max([1000, get(g:, 'toas_watch_first_frame_timeout_ms', 45000)])
  let l:inter_frame_timeout_ms = max([1000, get(g:, 'toas_watch_inter_frame_timeout_ms', 15000)])
  let l:last_activity_ms = get(l:pump, 'last_activity_ms', l:now_ms)
  let l:subscribe_started_ms = get(l:pump, 'subscribe_started_ms', l:last_activity_ms)
  let l:received_any_frames = get(l:pump, 'frame_ordinal', 0) > 0
  let l:idle_ms = l:now_ms - l:last_activity_ms
  let l:since_subscribe_ms = l:now_ms - l:subscribe_started_ms
  let l:timed_out = l:received_any_frames ? (l:idle_ms > l:inter_frame_timeout_ms) : (l:since_subscribe_ms > l:first_frame_timeout_ms)
  if l:timed_out
    call s:toas_wire_log('HARVEST_TIMEOUT run_id=' . a:run_id . ' pending=' . (has_key(l:pump, 'pending') ? len(l:pump.pending) : 0))
    " While the run is still live, timeout means this subscribe window went quiet.
    " Re-open subscribe instead of failing the watch loop.
    if get(l:pump, 'last_status', 'running') ==# 'running'
      let l:pump.phase = 'subscribe_send'
      let l:pump.request_id = ''
      let l:pump.subscribe_started_ms = l:now_ms
      let l:pump.last_activity_ms = l:now_ms
      let s:toas_watch_pump[a:run_id] = l:pump
      call s:toas_wire_log('HARVEST_TIMEOUT_RECOVER run_id=' . a:run_id . ' action=resubscribe')
      return {}
    endif
    if l:received_any_frames
      throw 'local_host timeout: no pushed frames in ' . float2nr(l:inter_frame_timeout_ms / 1000) . 's'
    endif
    throw 'local_host timeout: no first pushed frame in ' . float2nr(l:first_frame_timeout_ms / 1000) . 's'
  endif
  call s:toas_wire_log('HARVEST_IDLE run_id=' . a:run_id . ' pending=' . (has_key(l:pump, 'pending') ? len(l:pump.pending) : 0))
  return {}
endfunction

function! s:toas_merge_watch_like_frames(run_id, frames) abort
  if empty(a:frames)
    return {}
  endif
  let l:status = 'running'
  let l:events = []
  for l:frame in a:frames
    if type(l:frame) != type({})
      continue
    endif
    let l:payload = get(l:frame, 'payload', {})
    if type(l:payload) != type({})
      continue
    endif
    let l:s = s:toas_normalize_run_status(get(l:payload, 'status', 'running'))
    if s:toas_is_terminal_status(l:s)
      let l:status = l:s
    endif
    let l:evs = get(l:payload, 'events', [])
    if type(l:evs) == type([])
      call extend(l:events, l:evs)
    endif
  endfor
  return {
        \ 'protocol_version': 1,
        \ 'request_id': '',
        \ 'ok': v:true,
        \ 'payload': {
        \   'run_id': a:run_id,
        \   'status': l:status,
        \   'chunk': '',
        \   'events': l:events,
        \ },
        \ }
endfunction

function! s:toas_watch_pump_frame_to_response(run_id, parsed, pump, now_ms) abort
  if get(a:parsed, 'ok', v:false) != v:true
    let l:err = get(a:parsed, 'error', {})
    call s:toas_wire_log('ERROR op=watch request_id=' . string(get(a:parsed, 'request_id', '')) . ' message=' . string(get(l:err, 'message', 'unknown')))
    throw printf('local_host error: %s', get(l:err, 'message', 'unknown'))
  endif
  let l:payload = get(a:parsed, 'payload', {})
  let l:kind = get(l:payload, 'kind', '')
  if l:kind ==# 'push_complete'
    let l:complete = get(l:payload, 'complete', v:false) == v:true
    let a:pump.last_push_complete = l:complete ? 1 : 0
    call s:toas_wire_log('OK op=stream_subscribe request_id=' . string(get(a:parsed, 'request_id', '')) . ' kind=push_complete complete=' . (l:complete ? '1' : '0'))
    let l:last_status = s:toas_normalize_run_status(get(a:pump, 'last_status', 'running'))
    let l:status = l:last_status
    if l:complete
      if l:status ==# '' || l:status ==# 'running'
        let l:status = 'succeeded'
      endif
      let a:pump.phase = 'subscribe_send'
      let a:pump.request_id = ''
    else
      let l:status = 'running'
      " Non-terminal completion means this subscribe window ended; resubscribe.
      let a:pump.phase = 'subscribe_send'
      let a:pump.request_id = ''
    endif
    let a:pump.last_activity_ms = a:now_ms
    let s:toas_watch_pump[a:run_id] = a:pump
    let l:merged_chunk = ''
    let l:merged_events = []
    let l:merged_next_offset = get(s:toas_watch_offset, a:run_id, 0)
    let l:merged_next_seq = get(s:toas_watch_seq, a:run_id, 0)
    return {
          \ 'protocol_version': 1,
          \ 'request_id': get(a:parsed, 'request_id', ''),
          \ 'ok': v:true,
          \ 'payload': {
          \   'run_id': a:run_id,
          \   'status': l:status,
          \   'chunk': l:merged_chunk,
          \   'events': l:merged_events,
          \   'next_offset': l:merged_next_offset,
          \   'next_seq': l:merged_next_seq,
          \ },
          \ }
  endif
  if l:kind ==# 'push_event'
    let l:events = []
    let l:payload_events = get(l:payload, 'events', [])
    if type(l:payload_events) == type([]) && !empty(l:payload_events)
      let l:events = l:payload_events
    else
      let l:event = get(l:payload, 'event', {})
      if type(l:event) == type({}) && !empty(l:event)
        let l:events = [l:event]
      endif
    endif
    let l:status = 'running'
    for l:event in l:events
      let l:event_status = ''
      let l:event_type = type(l:event) == type({}) ? get(l:event, 'type', '') : ''
      if type(l:event) == type({})
        let l:raw_status = get(get(l:event, 'payload', {}), 'status', '')
        if type(l:raw_status) == type('')
          let l:event_status = tolower(l:raw_status)
        endif
      endif
      if l:event_status ==# 'completed'
        let l:event_status = 'succeeded'
      endif
      " Only treat explicit done events as authoritative for terminal status.
      if (l:event_type ==# 'llm_done' || l:event_type ==# 'run_done') && s:toas_is_terminal_status(l:event_status)
        let a:pump.last_status = l:event_status
        " Do not transition UI to terminal on event alone.
        " Commit terminality only when corresponding push_complete arrives.
        let l:status = 'running'
      elseif l:event_type ==# 'tool_done'
        if l:event_status ==# ''
          let l:ok = get(get(l:event, 'payload', {}), 'ok', v:null)
          if l:ok == v:true
            let l:event_status = 'succeeded'
          elseif l:ok == v:false
            let l:event_status = 'failed'
          endif
        endif
        if s:toas_is_terminal_status(l:event_status)
          let a:pump.last_status = l:event_status
          let l:status = 'running'
        endif
      endif
    endfor
    let a:pump.last_activity_ms = a:now_ms
    let s:toas_watch_pump[a:run_id] = a:pump
    return {'protocol_version': 1, 'request_id': get(a:parsed, 'request_id', ''), 'ok': v:true, 'payload': {'run_id': a:run_id, 'status': l:status, 'chunk': '', 'events': l:events}}
  endif
  let a:pump.last_activity_ms = a:now_ms
  let s:toas_watch_pump[a:run_id] = a:pump
  return {}
endfunction

function! s:toas_watch_debug_update(run_id, status, chunk_len, next_offset, next_seq, redraw, ...) abort
  let l:event_bytes_seen = (a:0 >= 1 && type(a:1) == type(0) && a:1 > 0) ? a:1 : 0
  if !has_key(s:toas_watch_debug, a:run_id)
    let s:toas_watch_debug[a:run_id] = {
          \ 'ticks': 0,
          \ 'redraws': 0,
          \ 'bytes_seen': 0,
          \ 'event_bytes_seen': 0,
          \ 'max_chunk_len': 0,
          \ 'history': [],
          \ 'last': {},
          \ }
  endif
  let s:toas_watch_debug[a:run_id].ticks += 1
  let s:toas_watch_debug[a:run_id].bytes_seen += a:chunk_len
  let s:toas_watch_debug[a:run_id].event_bytes_seen += l:event_bytes_seen
  if a:chunk_len > get(s:toas_watch_debug[a:run_id], 'max_chunk_len', 0)
    let s:toas_watch_debug[a:run_id].max_chunk_len = a:chunk_len
  endif
  if a:redraw
    let s:toas_watch_debug[a:run_id].redraws += 1
  endif
  call add(s:toas_watch_debug[a:run_id].history, {
        \ 'status': a:status,
        \ 'chunk_len': a:chunk_len,
        \ 'event_bytes_seen': l:event_bytes_seen,
        \ 'redraw': a:redraw ? v:true : v:false,
        \ 'next_offset': a:next_offset,
        \ 'next_seq': a:next_seq,
        \ })
  if len(s:toas_watch_debug[a:run_id].history) > 20
    call remove(s:toas_watch_debug[a:run_id].history, 0)
  endif
  let s:toas_watch_debug[a:run_id].last = {
        \ 'status': a:status,
        \ 'chunk_len': a:chunk_len,
        \ 'event_bytes_seen': l:event_bytes_seen,
        \ 'next_offset': a:next_offset,
        \ 'next_seq': a:next_seq,
        \ 'redraw': a:redraw ? v:true : v:false,
        \ }
endfunction

function! s:toas_record_lane(lane, fallback_reason) abort
  let g:toas_last_step_lane = a:lane
  let g:toas_last_step_fallback_reason = a:fallback_reason
endfunction

function! s:toas_ms_since(start) abort
  return float2nr(reltimefloat(reltime(a:start)) * 1000.0)
endfunction

function! s:toas_lane_order() abort
  if s:toas_transport_mode() ==# 'local_host' && get(g:, 'toas_local_host_debug_single_lane', 0)
    return ['default']
  endif
  if type(get(g:, 'toas_step_lane_order', [])) == type([])
    let l:order = copy(g:toas_step_lane_order)
    return empty(l:order) ? ['default', 'warm', 'cold', 'synchronous'] : l:order
  endif
  return ['default', 'warm', 'cold', 'synchronous']
endfunction

function! s:toas_lane_state(lane) abort
  if !has_key(s:toas_lane_health, a:lane)
    let s:toas_lane_health[a:lane] = {
          \ 'consecutive_failures': 0,
          \ 'cooldown_until_step': 0,
          \ 'last_error': '',
          \ }
  endif
  return s:toas_lane_health[a:lane]
endfunction

function! s:toas_lane_usable(lane) abort
  let l:state = s:toas_lane_state(a:lane)
  return s:toas_step_counter >= get(l:state, 'cooldown_until_step', 0)
endfunction

function! s:toas_note_lane_failure(lane, reason) abort
  let l:state = s:toas_lane_state(a:lane)
  let l:state.consecutive_failures = get(l:state, 'consecutive_failures', 0) + 1
  let l:state.last_error = a:reason
  let l:threshold = max([1, get(g:, 'toas_lane_failure_threshold', 2)])
  if l:state.consecutive_failures >= l:threshold
    let l:cooldown = max([1, get(g:, 'toas_lane_cooldown_steps', 3)])
    let l:state.cooldown_until_step = s:toas_step_counter + l:cooldown
  endif
  let s:toas_lane_health[a:lane] = l:state
endfunction

function! s:toas_note_lane_success(lane) abort
  let l:state = s:toas_lane_state(a:lane)
  let l:state.consecutive_failures = 0
  let l:state.cooldown_until_step = 0
  let l:state.last_error = ''
  let s:toas_lane_health[a:lane] = l:state
endfunction

function! s:toas_reset_async_lane_health_for_local_host() abort
  if s:toas_transport_mode() !=# 'local_host'
    return
  endif
  for l:lane in ['default', 'warm', 'cold']
    let l:state = s:toas_lane_state(l:lane)
    if get(l:state, 'last_error', '') =~# '^rpc channel not open'
      let l:state.consecutive_failures = 0
      let l:state.cooldown_until_step = 0
      let l:state.last_error = ''
      let s:toas_lane_health[l:lane] = l:state
    endif
  endfor
endfunction

function! s:toas_watch_tick(run_id, timer_id) abort
  let l:tick_start = reltime()
  let l:tick_start_ms = float2nr(reltimefloat(l:tick_start) * 1000.0)
  let l:tick_bookkeeping_start = reltime()
  let l:t_request_ms = 0
  let l:t_parse_ms = 0
  let l:t_render_ms = 0
  let l:t_decode_ms = 0
  let l:t_adapt_ms = 0
  let l:t_apply_ms = 0
  let l:t_apply_carriage_ms = 0
  let l:t_render_path_ms = 0
  let l:t_parse_residual_ms = 0
  let l:t_parse_fields_ms = 0
  let l:t_event_scan_ms = 0
  let l:t_progress_extract_ms = 0
  let l:t_pending_queue_ms = 0
  let l:t_region_lookup_ms = 0
  let l:t_tick_bookkeeping_ms = 0
  let l:t_render_prep_ms = 0
  let l:t_render_commit_ms = 0
  let l:render_mode = 'none'
  let l:phase_request_done_ms = l:tick_start_ms
  let l:phase_parse_done_ms = l:tick_start_ms
  let l:phase_apply_done_ms = l:tick_start_ms
  let l:phase_render_done_ms = l:tick_start_ms
  if get(s:toas_run_watch_ticks, a:run_id, 0) == 0
    call s:toas_phase_mark(a:run_id, 'first_tick')
    call s:toas_wire_log('WATCH_TICK_FIRST run_id=' . a:run_id)
  endif
  if !has_key(s:toas_run_buffers, a:run_id)
    call s:toas_stop_run_watcher(a:run_id)
    return
  endif
  let l:bufnr = s:toas_run_buffers[a:run_id]
  if !bufexists(l:bufnr) || !bufloaded(l:bufnr)
    call s:toas_stop_run_watcher(a:run_id)
    return
  endif
  let l:region_lookup_start = reltime()
  let l:region = s:toas_find_run_region(l:bufnr, a:run_id)
  let l:t_region_lookup_ms = s:toas_ms_since(l:region_lookup_start)
  if empty(l:region)
    call s:toas_stop_run_watcher(a:run_id)
    let g:toas_last_error = 'run region deleted for ' . a:run_id
    call s:toas_notice('toas watcher stopped: run region missing (' . a:run_id . ')')
    return
  endif

  let l:payload = {
        \ 'workdir': s:toas_workdir(),
        \ 'run_id': a:run_id,
        \ 'offset': get(s:toas_watch_offset, a:run_id, 0),
        \ 'since_seq': get(s:toas_watch_seq, a:run_id, 0),
        \ 'mode': 'poll',
        \ }
  try
    if has_key(s:toas_run_metrics, a:run_id) && !has_key(s:toas_run_metrics[a:run_id], 'first_watch_ms')
      let s:toas_run_metrics[a:run_id].first_watch_ms = s:toas_ms_since(s:toas_run_metrics[a:run_id].start_reltime)
    endif
    let l:phase_start = reltime()
    let l:parse_bookkeeping_start = reltime()
    if s:toas_transport_mode() ==# 'local_host'
      let l:resp = s:toas_watch_pump_tick(a:run_id, l:payload)
      let l:t_request_ms = s:toas_ms_since(l:phase_start)
      let l:phase_request_done_ms = float2nr(reltimefloat(reltime()) * 1000.0)
      let l:t_decode_ms = get(g:, 'toas_last_watch_decode_ms', 0)
      let l:t_adapt_ms = get(g:, 'toas_last_watch_adapt_ms', 0)
      if empty(l:resp)
        return
      endif
    else
      let l:resp = s:toas_request('watch', l:payload, 5.0)
      let l:t_request_ms = s:toas_ms_since(l:phase_start)
      let l:phase_request_done_ms = float2nr(reltimefloat(reltime()) * 1000.0)
    endif
    let s:toas_run_watch_ticks[a:run_id] = get(s:toas_run_watch_ticks, a:run_id, 0) + 1
    if get(s:toas_run_watch_ticks, a:run_id, 0) >= 5 && get(s:toas_run_watch_interval, a:run_id, 20) != 10
      if has_key(s:toas_run_timers, a:run_id)
        call timer_stop(s:toas_run_timers[a:run_id])
      endif
      let s:toas_run_timers[a:run_id] = timer_start(10, function('s:toas_watch_tick', [a:run_id]), {'repeat': -1})
      let s:toas_run_watch_interval[a:run_id] = 10
      if has_key(s:toas_run_metrics, a:run_id)
        let s:toas_run_metrics[a:run_id].watch_steady_ms = 10
      endif
    endif
    let l:phase_start = reltime()
    let l:parse_fields_start = reltime()
    let l:data = get(l:resp, 'payload', {})
    let l:chunk = get(l:data, 'chunk', '')
    let l:raw_chunk = l:chunk
    let l:error = get(l:data, 'error', '')
    let l:events = get(l:data, 'events', [])
    let l:stream_policy = get(l:data, 'stream_policy', {})
    let l:previous_progress = get(s:toas_run_progress, a:run_id, '')
    let l:event_text_appended = 0
    let l:event_bytes_appended = 0
    let l:event_chunk = ''
    if type(l:stream_policy) == type({}) && !empty(l:stream_policy)
      let s:toas_run_stream_policy[a:run_id] = l:stream_policy
    endif
    if !has_key(s:toas_run_text, a:run_id)
      let s:toas_run_text[a:run_id] = ''
    endif
    if !has_key(s:toas_run_seen_event_keys, a:run_id)
      let s:toas_run_seen_event_keys[a:run_id] = {}
    endif
    let l:t_parse_fields_ms = s:toas_ms_since(l:parse_fields_start)
    let l:event_scan_start = reltime()
    if type(l:events) == type([])
      for l:event in l:events
        if type(l:event) != type({})
          continue
        endif
        call s:toas_capture_error_event(a:run_id, l:event)
        let l:event_payload = get(l:event, 'payload', {})
        let l:event_id = get(l:event, 'id', '')
        let l:event_type = get(l:event, 'type', '')
        let l:event_seq = get(l:event, 'seq', '')
        let l:payload_event_id = type(l:event_payload) == type({}) ? get(l:event_payload, 'event_id', '') : ''
        let l:payload_ts = type(l:event_payload) == type({}) ? get(l:event_payload, 'ts', '') : ''
        let l:event_source = type(l:event_payload) == type({}) ? get(l:event_payload, 'source', '') : ''
        let l:has_stable_identity = (type(l:event_id) == type('') && l:event_id !=# '')
              \ || type(l:event_seq) == type(0)
              \ || (type(l:event_seq) == type('') && l:event_seq !=# '')
              \ || (type(l:payload_event_id) == type('') && l:payload_event_id !=# '')
              \ || (type(l:payload_ts) == type('') && l:payload_ts !=# '')
        let l:event_key = ''
        if l:has_stable_identity
          let l:event_key = string(l:event_seq) . '|' . string(l:event_id) . '|' . string(l:event_type) . '|' . string(l:payload_event_id) . '|' . string(l:payload_ts)
        endif
        if l:event_key !=# '' && has_key(s:toas_run_seen_event_keys[a:run_id], l:event_key)
          call s:toas_wire_log('EVENT_DEDUP_SKIP run_id=' . a:run_id . ' key=' . l:event_key)
          continue
        endif
        if l:event_key !=# ''
          let s:toas_run_seen_event_keys[a:run_id][l:event_key] = 1
        endif
        if l:event_source !=# 'watch_chunk_projection'
          if type(l:event_seq) == type(0)
            let s:toas_watch_seq[a:run_id] = max([get(s:toas_watch_seq, a:run_id, 0), l:event_seq])
          elseif type(l:event_seq) == type('') && l:event_seq =~# '^\d\+$'
            let s:toas_watch_seq[a:run_id] = max([get(s:toas_watch_seq, a:run_id, 0), str2nr(l:event_seq)])
          endif
        endif
        let l:event_text = s:toas_extract_renderable_event_text(a:run_id, l:event)
        if l:event_text !=# ''
          let l:event_text_appended = 1
          let l:event_bytes_appended += strlen(l:event_text)
          let l:event_chunk .= l:event_text
          let l:event_lane = get(l:event, 'lane', '')
          if l:event_lane ==# 'tool' || l:event_lane ==# 'llm_answer'
            let s:toas_run_last_content_lane[a:run_id] = l:event_lane
          endif
        endif
        if get(l:event, 'type', '') ==# 'prompt_progress' && s:toas_prompt_progress_enabled_for_run(a:run_id)
          let l:progress_text = s:toas_format_progress_event(get(l:event, 'payload', {}))
          if l:progress_text !=# ''
            let s:toas_run_progress[a:run_id] = l:progress_text
            call s:toas_prompt_progress_debug_note(a:run_id, l:progress_text)
          endif
        endif
      endfor
    endif
    let l:t_event_scan_ms = s:toas_ms_since(l:event_scan_start)
    let l:applied_chunk = ''
    let l:applied_source = ''
    if l:event_chunk !=# ''
      let l:applied_chunk = l:event_chunk
      let l:applied_source = 'events'
      if l:raw_chunk !=# '' && l:raw_chunk ==# l:event_chunk
        let l:applied_source = 'events_eq_raw'
      endif
    elseif l:raw_chunk !=# ''
      let l:applied_chunk = l:raw_chunk
      let l:applied_source = 'raw'
    endif
    let l:pending_queue_start = reltime()
    if !has_key(s:toas_run_pending_append, a:run_id)
      let s:toas_run_pending_append[a:run_id] = ''
    endif
    if l:applied_chunk !=# ''
      let s:toas_run_pending_append[a:run_id] .= l:applied_chunk
    endif
    let l:apply_budget = max([128, get(g:, 'toas_watch_apply_bytes_per_tick', 2048)])
    let l:pending = get(s:toas_run_pending_append, a:run_id, '')
    let l:to_apply = ''
    if l:pending !=# ''
      let l:to_apply = strpart(l:pending, 0, l:apply_budget)
      let s:toas_run_pending_append[a:run_id] = strpart(l:pending, strlen(l:to_apply))
    endif
    let l:t_pending_queue_ms = s:toas_ms_since(l:pending_queue_start)
    if l:to_apply !=# ''
      if get(get(s:toas_run_phase_ms, a:run_id, {}), 'first_render', -1) < 0
        call s:toas_phase_mark(a:run_id, 'first_render')
      endif
      if has_key(s:toas_watch_pump, a:run_id)
        let s:toas_watch_pump[a:run_id].bytes_applied = get(s:toas_watch_pump[a:run_id], 'bytes_applied', 0) + strlen(l:to_apply)
      endif
      call s:toas_wire_log('RENDER_INPUT run_id=' . a:run_id . ' source=' . l:applied_source . ' event_chunk_len=' . strlen(l:event_chunk) . ' raw_chunk_len=' . strlen(l:raw_chunk) . ' apply_len=' . strlen(l:to_apply) . ' pending_len=' . strlen(get(s:toas_run_pending_append, a:run_id, '')))
      let l:apply_carriage_start = reltime()
      let s:toas_run_text[a:run_id] = s:toas_apply_chunk_with_carriage(
            \ s:toas_run_text[a:run_id],
            \ l:to_apply,
            \ )
      let l:t_apply_carriage_ms = s:toas_ms_since(l:apply_carriage_start)
      let l:t_apply_ms = l:t_apply_carriage_ms
      call s:toas_wire_log('RUN_TEXT_APPLIED run_id=' . a:run_id . ' text_len=' . strlen(s:toas_run_text[a:run_id]))
      let l:progress_start = reltime()
      let l:progress_from_text = s:toas_extract_prompt_progress(s:toas_run_text[a:run_id])
      let l:t_progress_extract_ms = s:toas_ms_since(l:progress_start)
      if s:toas_prompt_progress_enabled_for_run(a:run_id) && l:progress_from_text !=# ''
        let s:toas_run_progress[a:run_id] = l:progress_from_text
        call s:toas_prompt_progress_debug_note(a:run_id, l:progress_from_text)
      endif
    endif
    let l:phase_apply_done_ms = float2nr(reltimefloat(reltime()) * 1000.0)
    let l:t_tick_bookkeeping_ms = s:toas_ms_since(l:parse_bookkeeping_start) - l:t_parse_fields_ms - l:t_event_scan_ms - l:t_pending_queue_ms - l:t_progress_extract_ms - l:t_apply_ms
    if l:t_tick_bookkeeping_ms < 0
      let l:t_tick_bookkeeping_ms = 0
    endif
    let l:t_parse_ms = s:toas_ms_since(l:phase_start)
    let l:phase_parse_done_ms = float2nr(reltimefloat(reltime()) * 1000.0)
    let l:t_parse_residual_ms = l:t_parse_ms - l:t_decode_ms - l:t_adapt_ms - l:t_apply_ms
          \ - l:t_parse_fields_ms - l:t_event_scan_ms - l:t_pending_queue_ms - l:t_progress_extract_ms - l:t_tick_bookkeeping_ms
    if l:t_parse_residual_ms < 0
      let l:t_parse_residual_ms = 0
    endif
    let s:toas_watch_offset[a:run_id] = get(l:data, 'next_offset', get(s:toas_watch_offset, a:run_id, 0))
    let s:toas_watch_seq[a:run_id] = get(l:data, 'next_seq', get(s:toas_watch_seq, a:run_id, 0))
    let l:status = get(l:data, 'status', 'running')
    let l:previous_status = get(s:toas_run_status, a:run_id, '')
    let l:progress_changed = get(s:toas_run_progress, a:run_id, '') !=# l:previous_progress
    let s:toas_run_status[a:run_id] = l:status
    let g:toas_last_run_status = l:status
    let g:toas_active_run_id = a:run_id
    let l:redraw = v:false
    if l:to_apply !=# '' || l:status !=# l:previous_status || l:progress_changed
      let l:phase_start = reltime()
      let l:render_prep_start = reltime()
      if (l:status ==# 'failed' || l:status ==# 'cancelled') && l:error !=# '' && get(s:toas_run_text, a:run_id, '') ==# ''
        let s:toas_run_text[a:run_id] = '[run ' . l:status . '] ' . s:toas_compact_error_message(l:error) . "\n"
      elseif (l:status ==# 'failed' || l:status ==# 'cancelled') && get(s:toas_run_text, a:run_id, '') ==# '' && get(s:toas_run_error_summary, a:run_id, '') !=# ''
        let s:toas_run_text[a:run_id] = '[run ' . l:status . '] ' . get(s:toas_run_error_summary, a:run_id, '') . "\n"
      endif
      call s:toas_wire_log('RUN_REGION_RENDER run_id=' . a:run_id . ' status=' . l:status . ' render_text_len=' . strlen(get(s:toas_run_text, a:run_id, '')))
      let l:t_render_prep_ms = s:toas_ms_since(l:render_prep_start)
      let l:render_commit_start = reltime()
      if l:status ==# 'running' && l:to_apply !=# ''
        let l:render_path_start = reltime()
        if !s:toas_append_run_region_chunk(a:run_id, l:status, l:to_apply)
          let l:render_mode = 'replace_fallback'
          call s:toas_replace_run_region(a:run_id, l:status, get(s:toas_run_text, a:run_id, ''), 1)
        else
          let l:render_mode = 'append'
        endif
        let l:t_render_path_ms = s:toas_ms_since(l:render_path_start)
      else
        let l:render_path_start = reltime()
        let l:render_mode = 'replace'
        call s:toas_replace_run_region(a:run_id, l:status, get(s:toas_run_text, a:run_id, ''), 1)
        let l:t_render_path_ms = s:toas_ms_since(l:render_path_start)
      endif
      let l:t_render_commit_ms = s:toas_ms_since(l:render_commit_start)
      let l:t_render_ms = s:toas_ms_since(l:phase_start)
      let l:phase_render_done_ms = float2nr(reltimefloat(reltime()) * 1000.0)
      let l:redraw = v:true
    endif
    let l:debug_chunk_len = strlen(l:chunk)
    if l:debug_chunk_len == 0 && l:event_bytes_appended > 0
      let l:debug_chunk_len = l:event_bytes_appended
    endif
    call s:toas_watch_debug_update(
          \ a:run_id,
          \ l:status,
          \ l:debug_chunk_len,
          \ get(l:data, 'next_offset', -1),
          \ get(l:data, 'next_seq', -1),
          \ l:redraw,
          \ l:event_bytes_appended,
          \ )
    if l:status ==# 'succeeded' || l:status ==# 'failed' || l:status ==# 'cancelled'
      " Terminal status must not drop buffered streamed text. Drain any pending append
      " before final projection/stop so late terminal probes can't truncate content.
      let l:remaining_pending = get(s:toas_run_pending_append, a:run_id, '')
      if l:remaining_pending !=# ''
        call s:toas_wire_log('TERMINAL_DRAIN run_id=' . a:run_id . ' pending_len=' . strlen(l:remaining_pending))
        let s:toas_run_text[a:run_id] = s:toas_apply_chunk_with_carriage(
              \ get(s:toas_run_text, a:run_id, ''),
              \ l:remaining_pending,
              \ )
        let s:toas_run_pending_append[a:run_id] = ''
      endif
      if get(s:toas_run_text, a:run_id, '') ==# ''
        try
          let l:backfill_payload = {
                \ 'workdir': s:toas_workdir(),
                \ 'run_id': a:run_id,
                \ 'offset': 0,
                \ 'since_seq': 0,
                \ 'mode': 'poll',
                \ }
          let l:backfill_resp = s:toas_request('watch', l:backfill_payload, 1.0)
          let l:backfill_data = get(l:backfill_resp, 'payload', {})
          let l:backfill_chunk = get(l:backfill_data, 'chunk', '')
          if type(l:backfill_chunk) == type('') && l:backfill_chunk !=# ''
            let s:toas_run_text[a:run_id] = s:toas_apply_chunk_with_carriage('', l:backfill_chunk)
            call s:toas_wire_log('TERMINAL_BACKFILL run_id=' . a:run_id . ' chunk_len=' . strlen(l:backfill_chunk))
          else
            call s:toas_wire_log('TERMINAL_BACKFILL run_id=' . a:run_id . ' chunk_len=0')
          endif
        catch
          call s:toas_wire_log('TERMINAL_BACKFILL_ERROR run_id=' . a:run_id . ' error=' . substitute(v:exception, "\n", ' ', 'g'))
        endtry
      endif
      let s:toas_run_progress[a:run_id] = ''
      if l:status ==# 'succeeded'
        " Successful completion drops sentinel markers and keeps canonical projection blocks only.
        let l:final_text = s:toas_extract_final_projection(get(s:toas_run_text, a:run_id, ''))
        let l:final_text = s:toas_ensure_projection_for_lane(l:final_text, get(s:toas_run_last_content_lane, a:run_id, ''))
        let l:final_text = substitute(l:final_text, "\%x00", "", "g")
        if l:final_text =~# '## RESULT\>' && l:final_text !~# '## TOAS:USER\>'
          let l:final_text = "## TOAS:USER\n\n\n\n" . l:final_text
        endif
        call s:toas_replace_run_region(a:run_id, l:status, l:final_text, 0)
      endif
      call s:toas_stop_run_watcher(a:run_id)
      if has_key(s:toas_run_metrics, a:run_id)
        let s:toas_run_metrics[a:run_id].total_ms = s:toas_ms_since(s:toas_run_metrics[a:run_id].start_reltime)
        let g:toas_last_step_timing = copy(s:toas_run_metrics[a:run_id])
        call remove(s:toas_run_metrics, a:run_id)
      endif
      if has_key(s:toas_run_stream_policy, a:run_id)
        call remove(s:toas_run_stream_policy, a:run_id)
      endif
      if has_key(s:toas_run_reasoning_open, a:run_id)
        call remove(s:toas_run_reasoning_open, a:run_id)
      endif
      if has_key(s:toas_run_prompt_progress_debug, a:run_id)
        let l:pp = s:toas_run_prompt_progress_debug[a:run_id]
        call s:toas_wire_log('PROMPT_PROGRESS_SUMMARY run_id=' . a:run_id . ' count=' . get(l:pp, 'count', 0) . ' first=' . string(get(l:pp, 'first', '')) . ' last=' . string(get(l:pp, 'last', '')))
        call remove(s:toas_run_prompt_progress_debug, a:run_id)
      endif
      let l:summary = s:toas_phase_summary(a:run_id)
      if l:summary !=# ''
        call s:toas_wire_log('PHASE_SUMMARY run_id=' . a:run_id . ' ' . l:summary)
      endif
      if has_key(s:toas_run_phase_ms, a:run_id)
        call remove(s:toas_run_phase_ms, a:run_id)
      endif
      call s:toas_wire_log_flush()
      call s:toas_notice(printf('toas run %s: %s', a:run_id, l:status))
    endif
    let l:tick_total_ms = s:toas_ms_since(l:tick_start)
    let l:tick_state = s:toas_tick_log_state_get(a:run_id)
    let l:tick_state.count += 1
    let l:emit_tick_log = (l:tick_state.count % s:toas_tick_log_every) == 0
    if l:status ==# 'succeeded' || l:status ==# 'failed' || l:status ==# 'cancelled'
      let l:emit_tick_log = 1
    endif
    if l:emit_tick_log && !s:toas_tick_edge_log_only
      call s:toas_wire_log(
            \ 'WATCH_TICK_TIMING_A'
            \ . ' run_id=' . a:run_id
            \ . ' tick=' . l:tick_state.count
            \ . ' total=' . l:tick_total_ms . 'ms'
            \ . ' region_lookup=' . l:t_region_lookup_ms . 'ms'
            \ . ' request=' . l:t_request_ms . 'ms'
            \ . ' parse=' . l:t_parse_ms . 'ms'
            \ . ' decode=' . l:t_decode_ms . 'ms'
            \ . ' adapt=' . l:t_adapt_ms . 'ms'
            \ . ' parse_fields=' . l:t_parse_fields_ms . 'ms'
            \ . ' event_scan=' . l:t_event_scan_ms . 'ms'
            \ . ' pending_queue=' . l:t_pending_queue_ms . 'ms'
            \ . ' progress_extract=' . l:t_progress_extract_ms . 'ms'
            \ . ' tick_bookkeeping=' . l:t_tick_bookkeeping_ms . 'ms'
            \ . ' apply=' . l:t_apply_ms . 'ms'
            \ . ' apply_carriage=' . l:t_apply_carriage_ms . 'ms'
            \ . ' parse_residual=' . l:t_parse_residual_ms . 'ms'
            \ )
      call s:toas_wire_log(
            \ 'WATCH_TICK_TIMING_B'
            \ . ' run_id=' . a:run_id
            \ . ' tick=' . l:tick_state.count
            \ . ' render=' . l:t_render_ms . 'ms'
            \ . ' render_prep=' . l:t_render_prep_ms . 'ms'
            \ . ' render_commit=' . l:t_render_commit_ms . 'ms'
            \ . ' render_path=' . l:t_render_path_ms . 'ms'
            \ . ' render_mode=' . l:render_mode
            \ . ' status=' . l:status
            \ . ' chunk_len=' . strlen(l:chunk)
            \ . ' redraw=' . (l:redraw ? '1' : '0')
            \ )
    endif
    if l:emit_tick_log
      call s:toas_wire_log(
            \ 'WATCH_TICK_BEGIN'
            \ . ' run_id=' . a:run_id
            \ . ' tick=' . l:tick_state.count
            \ . ' start_ms=' . float2nr(reltimefloat(l:tick_start) * 1000.0)
            \ . ' status=' . l:status
            \ )
      call s:toas_wire_log(
            \ 'WATCH_TICK_END'
            \ . ' run_id=' . a:run_id
            \ . ' tick=' . l:tick_state.count
            \ . ' total=' . l:tick_total_ms . 'ms'
            \ . ' status=' . l:status
            \ . ' redraw=' . (l:redraw ? '1' : '0')
            \ )
      if s:toas_tick_phase_edges_enabled()
        let l:edge_req = max([0, l:phase_request_done_ms - l:tick_start_ms])
        let l:edge_parse = max([0, l:phase_parse_done_ms - l:phase_request_done_ms])
        let l:edge_apply = max([0, l:phase_apply_done_ms - l:phase_parse_done_ms])
        let l:edge_render = max([0, l:phase_render_done_ms - l:phase_apply_done_ms])
        let l:edge_tail = max([0, float2nr(reltimefloat(reltime()) * 1000.0) - l:phase_render_done_ms])
        call s:toas_wire_log(
              \ 'WATCH_TICK_EDGES'
              \ . ' run_id=' . a:run_id
              \ . ' tick=' . l:tick_state.count
              \ . ' req=' . l:edge_req . 'ms'
              \ . ' parse=' . l:edge_parse . 'ms'
              \ . ' apply=' . l:edge_apply . 'ms'
              \ . ' render=' . l:edge_render . 'ms'
              \ . ' tail=' . l:edge_tail . 'ms'
              \ . ' total=' . l:tick_total_ms . 'ms')
      endif
    endif
  catch
    let g:toas_last_error = v:exception
    call s:toas_wire_log('WATCH_ERROR run_id=' . a:run_id . ' error=' . substitute(g:toas_last_error, "\n", ' ', 'g'))
    call s:toas_wire_log_flush()
    call s:toas_stop_run_watcher(a:run_id)
    call s:toas_notice('toas watcher error: ' . g:toas_last_error)
  endtry
endfunction

function! s:toas_start_nonblocking_step(insert_after, op_name, lane_name, ...) abort
  if !exists('*timer_start')
    throw 'timer support unavailable'
  endif
  call s:toas_wire_log('STEP_START lane=' . a:lane_name . ' op=' . a:op_name)
  let l:pending_id = a:0 >= 1 ? a:1 : 'pending-' . s:toas_request_id()
  let l:created_pending = a:0 == 0
  call s:toas_phase_mark(l:pending_id, 'step_start')
  if l:created_pending
    call s:toas_insert_run_region(l:pending_id, 'starting', a:insert_after)
  endif
  call s:toas_phase_mark(l:pending_id, 'marker')
  call s:toas_wire_log('RUN_MARKER_PENDING inserted=' . l:pending_id)
  let l:start = reltime()
  try
    let l:resp = s:toas_request(a:op_name, {'workdir': s:toas_workdir()}, 15.0)
  catch
    call s:toas_remove_run_region(l:pending_id)
    call remove(s:toas_run_buffers, l:pending_id)
    call remove(s:toas_run_status, l:pending_id)
    call remove(s:toas_run_progress, l:pending_id)
    throw 'nonblocking step start failed: ' . v:exception
  endtry
  let l:payload = get(l:resp, 'payload', {})
  let l:run_id = get(l:payload, 'run_id', '')
  if has_key(s:toas_run_phase_ms, l:pending_id)
    let s:toas_run_phase_ms[l:run_id] = copy(s:toas_run_phase_ms[l:pending_id])
  endif
  call s:toas_phase_mark(l:run_id, 'ack')
  call s:toas_wire_log('STEP_ACK run_id=' . l:run_id)
  let l:status = get(l:payload, 'status', 'running')
  let l:stream_policy = get(l:payload, 'stream_policy', {})
  if l:run_id ==# ''
    throw 'missing run_id in step_async response'
  endif
  let g:toas_active_run_id = l:run_id
  let g:toas_last_run_status = l:status
  let s:toas_watch_offset[l:run_id] = 0
  let s:toas_watch_seq[l:run_id] = 0
  let s:toas_run_text[l:run_id] = ''
  let s:toas_run_last_content_lane[l:run_id] = ''
  let s:toas_run_error_summary[l:run_id] = ''
  let s:toas_run_last_rendered_text[l:run_id] = ''
  let s:toas_run_stream_policy[l:run_id] = l:stream_policy
  let s:toas_run_reasoning_open[l:run_id] = 0
  let s:toas_run_watch_ticks[l:run_id] = 0
  let s:toas_run_watch_interval[l:run_id] = 20
  let s:toas_run_metrics[l:run_id] = {
        \ 'lane': a:lane_name,
        \ 'step_async_op': a:op_name,
        \ 'step_async_rpc_ms': s:toas_ms_since(l:start),
        \ 'watch_initial_ms': 20,
        \ 'watch_steady_ms': 50,
        \ 'start_reltime': reltime(),
        \ }
  let l:relabelled = s:toas_relabel_run_region(l:pending_id, l:run_id, l:status)
  if !l:relabelled
    call s:toas_insert_run_region(l:run_id, l:status, a:insert_after)
  endif
  if has_key(s:toas_run_buffers, l:pending_id)
    let s:toas_run_buffers[l:run_id] = s:toas_run_buffers[l:pending_id]
    call remove(s:toas_run_buffers, l:pending_id)
  endif
  if has_key(s:toas_run_status, l:pending_id)
    let s:toas_run_status[l:run_id] = l:status
    call remove(s:toas_run_status, l:pending_id)
  endif
  if has_key(s:toas_run_progress, l:pending_id)
    let s:toas_run_progress[l:run_id] = s:toas_run_progress[l:pending_id]
    call remove(s:toas_run_progress, l:pending_id)
  endif
  let l:timer = timer_start(20, function('s:toas_watch_tick', [l:run_id]), {'repeat': -1})
  let s:toas_run_timers[l:run_id] = l:timer
  return l:run_id
endfunction

function! s:toas_rpc_request(op, payload, timeout_s) abort
  if exists('g:ToasTestRpcRequestFn') && type(g:ToasTestRpcRequestFn) == type(function('tr'))
    return call(g:ToasTestRpcRequestFn, [a:op, a:payload, a:timeout_s])
  endif

  let g:toas_last_rpc_raw_len = -1
  let g:toas_last_rpc_stdout_len = -1
  if !s:toas_channel_open()
    throw 'rpc channel not open'
  endif

  let l:req = {
        \ 'protocol_version': 1,
        \ 'request_id': s:toas_request_id(),
        \ 'op': a:op,
        \ 'payload': a:payload,
        \ }

  call ch_sendraw(s:toas_channel, json_encode(l:req) . "\n")
  let l:raw = ''
  let l:deadline = reltimefloat(reltime()) + a:timeout_s
  while reltimefloat(reltime()) < l:deadline
    let l:chunk = ch_readraw(s:toas_channel, {'timeout': 250})
    if type(l:chunk) == type('') && l:chunk !=# ''
      let l:raw .= l:chunk
      if stridx(l:raw, "\n") >= 0
        break
      endif
    endif
  endwhile
  if l:raw ==# '' || stridx(l:raw, "\n") < 0
    throw 'empty or partial rpc response'
  endif
  let g:toas_last_rpc_raw_len = strlen(l:raw)
  let l:line = split(l:raw, "\n", 1)[0]
  let l:resp = json_decode(l:line)
  if type(l:resp) != type({})
    throw 'invalid rpc response'
  endif
  if get(l:resp, 'ok', v:false) != v:true
    let l:err = get(l:resp, 'error', {})
    throw printf('rpc error: %s', get(l:err, 'message', 'unknown'))
  endif
  let l:stdout = get(get(l:resp, 'payload', {}), 'stdout', '')
  let g:toas_last_rpc_stdout_len = strlen(l:stdout)
  return l:resp
endfunction

function! s:toas_transport_mode() abort
  let l:mode = get(g:, 'toas_transport_mode', 'local_host')
  " Fail-safe toward primary transport: unknown/non-string values intentionally
  " normalize to local_host instead of silently drifting to RPC behavior.
  if type(l:mode) != type('')
    return 'local_host'
  endif
  let l:mode = tolower(trim(l:mode))
  if l:mode ==# 'rpc_local_backend'
    return 'rpc_local_backend'
  endif
  if l:mode ==# 'local_host'
    return 'local_host'
  endif
  return 'local_host'
endfunction

function! s:toas_active_buffer_session_path() abort
  let l:buf_path = expand('%')
  if type(l:buf_path) != type('') || l:buf_path ==# ''
    return ''
  endif
  " Step intent is transcript intent: active buffer path string is authoritative target.
  return l:buf_path
endfunction

function! s:toas_request_payload(op, payload) abort
  let l:out = copy(a:payload)
  if has_key(l:out, 'workdir') && type(l:out.workdir) == type('')
    let l:out.workdir = s:toas_normalize_workdir_root(l:out.workdir)
  endif
  if a:op ==# 'step' || a:op ==# 'step_async' || a:op ==# 'step_async_warm' || a:op ==# 'step_async_cold'
    if !has_key(l:out, 'session') && !has_key(l:out, 'session_path')
      let l:session_path = s:toas_active_buffer_session_path()
      if l:session_path !=# ''
        let l:out.session = l:session_path
      endif
    endif
  endif
  if s:toas_transport_mode() ==# 'rpc_local_backend' || s:toas_transport_mode() ==# 'local_host'
    if a:op ==# 'step_async' || a:op ==# 'step_async_warm' || a:op ==# 'step_async_cold' || a:op ==# 'watch' || a:op ==# 'cancel'
      let l:out.backend_mode = 'local'
    endif
  endif
  return l:out
endfunction

function! s:toas_request(op, payload, timeout_s) abort
  " Routing contract: async lifecycle ops (`step_async*`, `watch`, `cancel`)
  " are primary-routed through local host when selected; other ops keep RPC path.
  if s:toas_transport_mode() ==# 'local_host'
    if a:op ==# 'step_async' || a:op ==# 'step_async_warm' || a:op ==# 'step_async_cold' || a:op ==# 'watch' || a:op ==# 'cancel'
      return s:toas_local_host_request(a:op, s:toas_request_payload(a:op, a:payload), a:timeout_s)
    endif
  endif
  return s:toas_rpc_request(a:op, s:toas_request_payload(a:op, a:payload), a:timeout_s)
endfunction

function! s:toas_local_host_request(op, payload, timeout_s) abort
  if exists('g:ToasTestLocalHostRequestFn') && type(g:ToasTestLocalHostRequestFn) == type(function('tr'))
    return call(g:ToasTestLocalHostRequestFn, [a:op, a:payload, a:timeout_s])
  endif
  if !exists('*job_getchannel')
    throw 'local_host unavailable: missing job_getchannel'
  endif
  if !s:toas_host_ensure_started()
    throw 'local_host unavailable: host process not running'
  endif
  if s:toas_host_channel is v:null || ch_status(s:toas_host_channel) !=# 'open'
    throw 'local_host unavailable: host channel not open'
  endif

  let l:req = {
        \ 'protocol_version': 1,
        \ 'request_id': s:toas_request_id(),
        \ 'op': a:op,
        \ 'payload': a:payload,
        \ }
  let l:resp = v:null
  let l:last_parsed = v:null
  let l:attempt = 0
  let l:allow_host_refresh = a:op ==# 'step_async' || a:op ==# 'step_async_warm' || a:op ==# 'step_async_cold'
  while l:attempt < 2
    let l:attempt += 1
    let l:expect_id = l:req.request_id
    call s:toas_wire_log('SEND op=' . a:op . ' request_id=' . l:expect_id . ' attempt=' . l:attempt)
    try
      call ch_sendraw(s:toas_host_channel, json_encode(l:req) . "\n")
    catch
      if l:allow_host_refresh && l:attempt < 2 && v:exception =~# 'E630'
        call s:toas_host_reset('ch_sendraw disconnected')
        call s:toas_host_ensure_started()
        continue
      endif
      throw v:exception
    endtry
    let l:deadline = reltimefloat(reltime()) + (a:timeout_s > 0.0 ? a:timeout_s : 0.001)
    let l:read_timeout_ms = (a:op ==# 'watch') ? 8 : 250
    let l:max_reads = (a:op ==# 'watch') ? 3 : -1
    let l:reads = 0
    while reltimefloat(reltime()) <= l:deadline
      " Windows/Vim channel callback delivery can lag for stdio host output.
      " Pull directly from the channel as a bounded fallback so request start
      " does not fail with an empty buffer when a full line is already available.
      try
        let l:direct_chunk = ch_readraw(s:toas_host_channel, {'timeout': l:read_timeout_ms})
      catch
        let l:direct_chunk = ''
      endtry
      if type(l:direct_chunk) == type('') && l:direct_chunk !=# ''
        let s:toas_host_rx_buffer .= l:direct_chunk
      endif

      let l:norm = substitute(s:toas_host_rx_buffer, "\%x00", '', 'g')
      let l:parts = split(l:norm, "\n", 1)
      if len(l:parts) > 1
        let l:tail = l:parts[-1]
        let l:unmatched = []
        for l:i in range(0, len(l:parts) - 2)
          let l:part = l:parts[l:i]
          if l:part ==# ''
            continue
          endif
          try
            let l:parsed = json_decode(l:part)
            if type(l:parsed) == type({})
              call s:toas_wire_log('RECV request_id=' . string(get(l:parsed, 'request_id', '')) . ' ok=' . string(get(l:parsed, 'ok', v:false)) . ' line_len=' . strlen(l:part))
              let l:last_parsed = l:parsed
              if get(l:parsed, 'request_id', '') ==# l:expect_id
                let l:resp = l:parsed
                break
              else
                call add(l:unmatched, l:part)
              endif
            else
              call add(l:unmatched, l:part)
            endif
          catch
            " Keep undecodable lines for later consumers; they may complete or belong elsewhere.
            call add(l:unmatched, l:part)
          endtry
        endfor
        if empty(l:unmatched)
          let s:toas_host_rx_buffer = l:tail
        else
          let s:toas_host_rx_buffer = join(l:unmatched, "\n") . "\n" . l:tail
        endif
        if l:resp isnot v:null
          break
        endif
      endif

      let l:reads += 1
      if a:op ==# 'watch' && l:reads >= l:max_reads
        break
      endif
      sleep 10m
    endwhile
    if l:resp isnot v:null
      break
    endif
    if !l:allow_host_refresh
      break
    endif
    " Retry once after refreshing channel/host to handle transient startup pipe state.
    let s:toas_host_channel = v:null
    call s:toas_host_ensure_started()
    if s:toas_host_channel is v:null || ch_status(s:toas_host_channel) !=# 'open'
      break
    endif
  endwhile
  if l:resp is v:null && type(l:last_parsed) == type({})
    call s:toas_wire_log('FALLBACK request_id=' . string(get(l:last_parsed, 'request_id', '')))
    let l:resp = l:last_parsed
  endif
  if l:resp is v:null
    call s:toas_wire_log('FAIL op=' . a:op . ' reason=empty_or_partial')
    throw 'empty or partial local_host response'
  endif
  if type(l:resp) != type({})
    throw 'invalid local_host response'
  endif
  if get(l:resp, 'ok', v:false) != v:true
    let l:err = get(l:resp, 'error', {})
    call s:toas_wire_log('ERROR op=' . a:op . ' request_id=' . string(get(l:resp, 'request_id', '')) . ' message=' . string(get(l:err, 'message', 'unknown')))
    throw printf('local_host error: %s', get(l:err, 'message', 'unknown'))
  endif
  call s:toas_wire_log('OK op=' . a:op . ' request_id=' . string(get(l:resp, 'request_id', '')))
  return l:resp
endfunction

function! s:toas_local_host_subscribe_frames(run_id, timeout_s) abort
  " Compatibility helper: this blocking collector is kept for fallback watch paths
  " and tests. Primary follow behavior is timer/callback push processing.
  if exists('g:ToasTestLocalHostSubscribeFn') && type(g:ToasTestLocalHostSubscribeFn) == type(function('tr'))
    return call(g:ToasTestLocalHostSubscribeFn, [a:run_id, a:timeout_s])
  endif
  if !exists('*job_getchannel')
    throw 'local_host unavailable: missing job_getchannel'
  endif
  if !s:toas_host_ensure_started()
    throw 'local_host unavailable: host process not running'
  endif
  if s:toas_host_channel is v:null || ch_status(s:toas_host_channel) !=# 'open'
    throw 'local_host unavailable: host channel not open'
  endif

  if !has_key(s:toas_watch_offset, a:run_id)
    let s:toas_watch_offset[a:run_id] = 0
  endif
  if !has_key(s:toas_watch_seq, a:run_id)
    let s:toas_watch_seq[a:run_id] = 0
  endif
  let l:req = {
        \ 'protocol_version': 1,
        \ 'request_id': s:toas_request_id(),
        \ 'op': 'stream_subscribe',
        \ 'payload': {
        \   'run_id': a:run_id,
        \   'timeout_s': a:timeout_s,
        \   'offset': get(s:toas_watch_offset, a:run_id, 0),
        \   'since_seq': get(s:toas_watch_seq, a:run_id, 0),
        \ },
        \ }
  let l:frames = []
  call ch_sendraw(s:toas_host_channel, json_encode(l:req) . "\n")
  let l:deadline = reltimefloat(reltime()) + a:timeout_s + 1.0
  while reltimefloat(reltime()) < l:deadline
    let l:norm = substitute(s:toas_host_rx_buffer, "\%x00", '', 'g')
    let l:parts = split(l:norm, "\n", 1)
    if len(l:parts) > 1
      let s:toas_host_rx_buffer = l:parts[-1]
      for l:i in range(0, len(l:parts) - 2)
        let l:part = l:parts[l:i]
        if l:part ==# ''
          continue
        endif
        try
          let l:parsed = json_decode(l:part)
          if type(l:parsed) != type({})
            continue
          endif
          if get(l:parsed, 'request_id', '') !=# l:req.request_id
            continue
          endif
          if get(l:parsed, 'ok', v:false) != v:true
            let l:err = get(l:parsed, 'error', {})
            throw printf('local_host error: %s', get(l:err, 'message', 'unknown'))
          endif
          call add(l:frames, l:parsed)
          let l:kind = get(get(l:parsed, 'payload', {}), 'kind', '')
          if l:kind ==# 'push_event'
            let l:event = get(get(l:parsed, 'payload', {}), 'event', {})
            let l:seq = get(l:event, 'seq', -1)
            if type(l:seq) == type(0) && l:seq >= 0
              let s:toas_watch_seq[a:run_id] = max([get(s:toas_watch_seq, a:run_id, 0), l:seq])
            endif
          endif
          if l:kind ==# 'push_complete'
            return l:frames
          endif
        catch
          " Ignore undecodable or partial frames.
        endtry
      endfor
    endif
    sleep 10m
  endwhile
  return l:frames
endfunction

function! s:toas_run_sync_cli_step() abort
  let l:cwd_save = getcwd()
  try
    execute 'lcd! ' . fnameescape(s:toas_workdir())
    return system('toas step')
  finally
    execute 'lcd! ' . fnameescape(l:cwd_save)
  endtry
endfunction

function! s:toas_try_step_lane(lane, insert_after, pending_id) abort
  if a:lane ==# 'default'
    if !get(g:, 'toas_step_nonblocking', 0) || !exists('*timer_start')
      throw 'default lane unavailable: nonblocking timer path disabled'
    endif
    let l:run_id = s:toas_start_nonblocking_step(a:insert_after, 'step_async', 'default', a:pending_id)
    let g:toas_last_step_transport = s:toas_transport_mode() ==# 'local_host' ? 'local_host_async_nonblocking' : 'rpc_async_nonblocking'
    return {'kind': 'async_started', 'run_id': l:run_id}
  endif

  if a:lane ==# 'warm'
    if !get(g:, 'toas_step_nonblocking', 0) || !exists('*timer_start')
      throw 'warm lane unavailable: nonblocking timer path disabled'
    endif
    let l:run_id = s:toas_start_nonblocking_step(a:insert_after, 'step_async_warm', 'warm', a:pending_id)
    let g:toas_last_step_transport = s:toas_transport_mode() ==# 'local_host' ? 'local_host_async_nonblocking' : 'rpc_async_nonblocking'
    return {'kind': 'async_started', 'run_id': l:run_id}
  endif

  if a:lane ==# 'cold'
    let l:out = s:toas_step_rpc_async_collect()
    let g:toas_last_step_transport = 'rpc_async'
    return {'kind': 'sync_output', 'out': l:out}
  endif

  if a:lane ==# 'synchronous'
    if s:toas_transport_mode() ==# 'local_host'
      throw 'local_host: synchronous lane disabled while async transport selected'
    endif
    try
      let l:out = s:toas_step_rpc()
      let g:toas_last_step_transport = 'rpc'
      return {'kind': 'sync_output', 'out': l:out}
    catch
      let s:toas_channel = v:null
      let g:toas_last_step_transport = 'cli_fallback'
      return {'kind': 'sync_output', 'out': s:toas_run_sync_cli_step()}
    endtry
  endif

  throw 'unknown step lane: ' . a:lane
endfunction

function! ToasStep() abort
  " ensure disk is current
  if &modified
    write
  endif

  call s:toas_host_ensure_started()
  call s:toas_reset_async_lane_health_for_local_host()
  let s:toas_step_counter += 1
  let l:fallbacks = []
  let g:toas_last_error = ''
  if s:toas_transport_mode() ==# 'local_host'
    let g:toas_last_step_transport = 'local_host_pending'
  endif
  let g:toas_last_step_timing = {}
  let l:pending_id = 'pending-' . s:toas_request_id()
  call s:toas_insert_run_region(l:pending_id, 'starting', line('$'))
  redraw

  for l:lane in s:toas_lane_order()
    if !s:toas_lane_usable(l:lane)
      let l:state = s:toas_lane_state(l:lane)
      call add(l:fallbacks, printf('%s: cooling down until step %d', l:lane, get(l:state, 'cooldown_until_step', 0)))
      continue
    endif
    try
      let l:result = s:toas_try_step_lane(l:lane, line('$'), l:pending_id)
      call s:toas_note_lane_success(l:lane)
      call s:toas_record_lane(l:lane, join(l:fallbacks, ' | '))
      let g:toas_last_error = ''
      if l:result.kind ==# 'async_started'
        call s:toas_notice(printf('toas async run started: %s', l:result.run_id))
        return
      endif
      let l:out = get(l:result, 'out', '')
      if l:out !=# ''
        call append(line('$'), split(substitute(l:out, '\r', '', 'g'), "\n"))
        normal! G
      endif
      return
    catch
      let l:lane_error = v:exception
      if l:lane_error ==# ''
        let l:lane_error = printf('unknown vim error at %s', v:throwpoint)
      endif
      call s:toas_remove_run_region(l:pending_id)
      if has_key(s:toas_run_buffers, l:pending_id) | call remove(s:toas_run_buffers, l:pending_id) | endif
      if has_key(s:toas_run_status, l:pending_id) | call remove(s:toas_run_status, l:pending_id) | endif
      if has_key(s:toas_run_progress, l:pending_id) | call remove(s:toas_run_progress, l:pending_id) | endif
      call s:toas_note_lane_failure(l:lane, l:lane_error)
      call add(l:fallbacks, printf('%s: %s', l:lane, l:lane_error))
      let g:toas_last_error = l:lane_error
    endtry
  endfor

  " unreachable in normal policy because synchronous lane includes CLI fallback.
  call s:toas_record_lane('none', join(l:fallbacks, ' | '))
  if s:toas_transport_mode() ==# 'local_host'
    let g:toas_last_step_transport = 'local_host_error'
  endif
  if g:toas_last_error ==# ''
    let g:toas_last_error = 'unknown failure (no lane error captured)'
  endif
  echoerr 'ToasStep failed: ' . g:toas_last_error
endfunction

command! ToasStep call ToasStep()
nnoremap <leader>s :ToasStep<CR>

function! ToasStepAsync() abort
  if &modified
    write
  endif

  try
    call s:toas_host_ensure_started()
    let l:resp = s:toas_request('step_async', {'workdir': s:toas_workdir()}, 15.0)
    let l:payload = get(l:resp, 'payload', {})
    let l:run_id = get(l:payload, 'run_id', '')
    let l:status = get(l:payload, 'status', '')
    if l:run_id ==# ''
      throw 'missing run_id in step_async response'
    endif
    let g:toas_active_run_id = l:run_id
    let g:toas_last_run_status = l:status
    let s:toas_watch_offset[l:run_id] = 0
    let s:toas_watch_seq[l:run_id] = 0
    let g:toas_last_step_transport = s:toas_transport_mode() ==# 'local_host' ? 'local_host_async' : 'rpc'
    let g:toas_last_error = ''
    call s:toas_notice(printf('toas async run started: %s (%s)', l:run_id, l:status))
  catch
    let g:toas_last_error = v:exception
    if s:toas_transport_mode() ==# 'local_host'
      let g:toas_last_step_transport = 'local_host_error'
      echoerr 'ToasStepAsync failed: ' . g:toas_last_error
      return
    endif
    let s:toas_channel = v:null
    let g:toas_last_step_transport = 'cli_fallback'
    let l:cwd_save = getcwd()
    try
      execute 'lcd! ' . fnameescape(s:toas_workdir())
      let l:out = system('toas step --async')
    finally
      execute 'lcd! ' . fnameescape(l:cwd_save)
    endtry
    let l:match = matchlist(l:out, 'run_id=\(\S\+\)')
    if len(l:match) >= 2
      let g:toas_active_run_id = l:match[1]
      let g:toas_last_run_status = 'running'
      let s:toas_watch_offset[g:toas_active_run_id] = 0
      let s:toas_watch_seq[g:toas_active_run_id] = 0
      call s:toas_notice(printf('toas async run started: %s (running)', g:toas_active_run_id))
      return
    endif
    echoerr 'ToasStepAsync failed: ' . g:toas_last_error
  endtry
endfunction

function! ToasWatch(...) abort
  let l:run_id = get(g:, 'toas_active_run_id', '')
  if a:0 >= 1 && a:1 !=# '' && a:1 !~# '^--'
    let l:run_id = a:1
  endif
  if l:run_id ==# ''
    echoerr 'ToasWatch requires run_id or g:toas_active_run_id'
    return
  endif

  let l:follow = 0
  for l:arg in a:000
    if l:arg ==# '--follow'
      let l:follow = 1
    endif
  endfor

  if !has_key(s:toas_watch_offset, l:run_id)
    let s:toas_watch_offset[l:run_id] = 0
  endif
  if !has_key(s:toas_watch_seq, l:run_id)
    let s:toas_watch_seq[l:run_id] = 0
  endif

  " Keep manual watch cursor independent when a nonblocking timer watcher is active
  " for the same run_id; otherwise, ToasWatch and timer ticks can steal chunks
  " from each other by racing shared offset/seq advancement.
  let l:use_local_cursor = has_key(s:toas_run_timers, l:run_id)
  let l:local_offset = l:use_local_cursor ? 0 : get(s:toas_watch_offset, l:run_id, 0)
  let l:local_seq = l:use_local_cursor ? 0 : get(s:toas_watch_seq, l:run_id, 0)

  while 1
    if s:toas_transport_mode() ==# 'local_host' && l:follow
      try
        " Preferred follow path: subscribe/push stream consumption.
        let l:frames = s:toas_local_host_subscribe_frames(l:run_id, 5.0)
        let l:terminal_seen = 0
        for l:frame in l:frames
          let l:pl = get(l:frame, 'payload', {})
          let l:kind = get(l:pl, 'kind', '')
          if l:kind ==# 'push_event'
            let l:event = get(l:pl, 'event', {})
            if get(l:event, 'lane', '') ==# 'llm_answer' && get(l:event, 'phase', '') ==# 'delta'
              let l:text = get(get(l:event, 'payload', {}), 'text', '')
              if l:text !=# ''
                call append(line('$'), split(substitute(l:text, '\r', '', 'g'), "\n"))
                normal! G
              endif
            elseif get(l:event, 'lane', '') ==# 'tool' && get(l:event, 'phase', '') ==# 'delta'
              let l:text = get(get(l:event, 'payload', {}), 'text', '')
              if l:text !=# ''
                call append(line('$'), split(substitute(l:text, '\r', '', 'g'), "\n"))
                normal! G
              endif
            elseif get(l:event, 'lane', '') ==# 'llm_answer' && get(l:event, 'phase', '') ==# 'end'
              let l:status = s:toas_normalize_run_status(get(get(l:event, 'payload', {}), 'status', ''))
              if l:status !=# ''
                let g:toas_last_run_status = l:status
                if s:toas_is_terminal_status(l:status)
                  let l:terminal_seen = 1
                endif
              endif
            endif
          elseif l:kind ==# 'push_complete'
            let l:complete = get(l:pl, 'complete', v:false)
            if l:complete == v:true && g:toas_last_run_status ==# ''
              let g:toas_last_run_status = 'succeeded'
              let l:terminal_seen = 1
            elseif l:complete == v:true && s:toas_is_terminal_status(g:toas_last_run_status)
              let l:terminal_seen = 1
            endif
          endif
        endfor
        let g:toas_active_run_id = l:run_id
        call s:toas_notice(printf('toas run %s: %s', l:run_id, g:toas_last_run_status ==# '' ? 'running' : g:toas_last_run_status))
        if l:terminal_seen
          break
        endif
      catch
        " Fallback policy is deliberate: preserve operator continuity by falling
        " back to watch poll/follow on transport/channel transients.
        " Accepted fallback-trigger classes here:
        " - local_host availability/channel startup issues
        " - write/read partial-response transients from host channel
        if exists('g:ToasTestLocalHostRequestFn') && type(g:ToasTestLocalHostRequestFn) == type(function('tr'))
          " test seam: use watch stub flow
        elseif v:exception !~# 'local_host unavailable' && v:exception !~# 'ch_sendraw' && v:exception !~# 'empty or partial local_host response'
          let g:toas_last_error = v:exception
          echoerr 'ToasWatch failed: ' . g:toas_last_error
          return
        endif
      endtry
    endif

    let l:payload = {
          \ 'workdir': s:toas_workdir(),
          \ 'run_id': l:run_id,
          \ 'offset': l:use_local_cursor ? l:local_offset : get(s:toas_watch_offset, l:run_id, 0),
          \ 'since_seq': l:use_local_cursor ? l:local_seq : get(s:toas_watch_seq, l:run_id, 0),
          \ 'mode': l:follow ? 'follow' : 'poll',
          \ }
    try
      let l:resp = s:toas_request('watch', l:payload, 5.0)
      let l:data = get(l:resp, 'payload', {})
      let l:events = get(l:data, 'events', [])
      let l:text = s:toas_collect_event_text(l:events)
      if l:text ==# ''
        let l:text = get(l:data, 'chunk', '')
      endif
      if l:text !=# ''
        call append(line('$'), split(substitute(l:text, '\r', '', 'g'), "\n"))
        normal! G
      endif
      if l:use_local_cursor
        let l:local_offset = get(l:data, 'next_offset', l:local_offset)
        let l:local_seq = get(l:data, 'next_seq', l:local_seq)
      else
        let s:toas_watch_offset[l:run_id] = get(l:data, 'next_offset', get(s:toas_watch_offset, l:run_id, 0))
        let s:toas_watch_seq[l:run_id] = get(l:data, 'next_seq', get(s:toas_watch_seq, l:run_id, 0))
      endif
      let l:status = s:toas_normalize_run_status(get(l:data, 'status', ''))
      let g:toas_last_run_status = l:status
      let g:toas_active_run_id = l:run_id
      if s:toas_is_terminal_status(l:status)
        call s:toas_notice(printf('toas run %s: %s', l:run_id, l:status))
        break
      endif
      if !l:follow
        call s:toas_notice(printf('toas run %s: %s', l:run_id, l:status))
        break
      endif
      sleep 100m
    catch
      let g:toas_last_error = v:exception
      echoerr 'ToasWatch failed: ' . g:toas_last_error
      return
    endtry
  endwhile
endfunction

function! ToasCancel(...) abort
  let l:run_id = get(g:, 'toas_active_run_id', '')
  let l:run_source = 'g:toas_active_run_id'
  if a:0 >= 1 && a:1 !=# ''
    let l:run_id = a:1
    let l:run_source = 'arg'
  endif
  call s:toas_wire_log(
        \ 'CANCEL_ENTRY arg_count=' . a:0
        \ . ' arg1=' . string(a:0 >= 1 ? a:1 : '')
        \ . ' active_run_id=' . string(get(g:, 'toas_active_run_id', ''))
        \ )
  if l:run_id ==# ''
    call s:toas_wire_log('CANCEL_ABORT reason=missing_run_id')
    call s:toas_wire_log_flush()
    echoerr 'ToasCancel requires run_id or g:toas_active_run_id'
    return
  endif
  let l:raw_workdir = s:toas_workdir()
  let l:effective_workdir = s:toas_normalize_workdir_root(l:raw_workdir)
  let l:payload = {'workdir': l:effective_workdir, 'run_id': l:run_id}
  call s:toas_wire_log(
        \ 'CANCEL_SELECTED run_id=' . l:run_id
        \ . ' source=' . l:run_source
        \ . ' raw_workdir=' . string(l:raw_workdir)
        \ . ' effective_workdir=' . string(l:effective_workdir)
        \ . ' payload=' . string(l:payload)
        \ )
  try
    let l:resp = s:toas_request('cancel', l:payload, 15.0)
    let l:data = get(l:resp, 'payload', {})
    let l:status = s:toas_normalize_run_status(get(l:data, 'status', ''))
    let g:toas_last_run_status = l:status
    let g:toas_active_run_id = l:run_id
    call s:toas_wire_log(
          \ 'CANCEL_RESPONSE run_id=' . l:run_id
          \ . ' status=' . l:status
          \ . ' payload=' . string(l:data)
          \ )
    call s:toas_wire_log_flush()
    call s:toas_notice(printf('toas run %s: %s', l:run_id, l:status))
  catch
    let g:toas_last_error = v:exception
    call s:toas_wire_log('CANCEL_ERROR run_id=' . l:run_id . ' error=' . substitute(g:toas_last_error, "\n", ' ', 'g'))
    call s:toas_wire_log_flush()
    echoerr 'ToasCancel failed: ' . g:toas_last_error
  endtry
endfunction

function! ToasStepHere() abort
  if &modified
    write
  endif

  let l:cur = line('.')
  let l:tail = getline(l:cur + 1, '$')

  " truncate buffer to cursor
  execute (l:cur + 1) . ',$delete _'

  " write truncated state for TOAS input
  write

  if get(g:, 'toas_step_nonblocking', 0) && exists('*timer_start')
    try
      let l:run_id = s:toas_start_nonblocking_step(line('$'), 'step_async', 'default')
      let g:toas_last_step_transport = 'rpc_async_nonblocking'
      call s:toas_record_lane('default', '')
      let g:toas_last_error = ''
      " reattach tail immediately; stream writes stay in sentinel run region.
      if !empty(l:tail)
        call append(line('$'), l:tail)
      endif
      call s:toas_notice(printf('toas async run started: %s', l:run_id))
      return
    catch
      call s:toas_record_lane('default', v:exception)
      let g:toas_last_error = v:exception
    endtry
  endif

  " run step (RPC preferred, fallback CLI)
  try
    let l:out = s:toas_step_rpc_async_collect()
    let g:toas_last_step_transport = 'rpc_async'
    let g:toas_last_error = ''
  catch
    try
      let l:out = s:toas_step_rpc()
      let g:toas_last_step_transport = 'rpc'
      let g:toas_last_error = ''
    catch
      let g:toas_last_error = v:exception
      if s:toas_transport_mode() ==# 'local_host'
        let g:toas_last_step_transport = 'local_host_error'
        echoerr 'ToasStepHere failed: ' . g:toas_last_error
        if !empty(l:tail)
          call append(line('$'), l:tail)
        endif
        return
      endif
      let s:toas_channel = v:null
      let g:toas_last_step_transport = 'cli_fallback'
      let l:cwd_save = getcwd()
      try
        execute 'lcd! ' . fnameescape(s:toas_workdir())
        let l:out = system('toas step')
      finally
        execute 'lcd! ' . fnameescape(l:cwd_save)
      endtry
    endtry
  endtry

  let l:out = substitute(l:out, '\r', '', 'g')
  call append(line('$'), split(l:out, "\n"))

  " reattach tail
  if !empty(l:tail)
    call append(line('$'), l:tail)
  endif

  normal! G
endfunction

function! s:toas_reset_runtime_state() abort
  if exists('*ch_close')
    try
      if s:toas_channel isnot v:null
        call ch_close(s:toas_channel)
      endif
    catch
    endtry
  endif
  let s:toas_channel = v:null
  let s:toas_host_channel = v:null
  let s:toas_host_rx_buffer = ''
  let s:toas_host_start_cmd = []
  let s:toas_host_last_exit = v:null
  let s:toas_host_stderr_tail = []
  let s:toas_host_start_time = v:null
  let s:toas_host_launch_transport = ''
  let s:toas_watch_offset = {}
  let s:toas_watch_seq = {}
  let s:toas_run_text = {}
  let s:toas_run_progress = {}
  let s:toas_run_status = {}
  let s:toas_run_seen_event_keys = {}
  let s:toas_run_last_content_lane = {}
  let s:toas_run_error_summary = {}
  let s:toas_run_stream_policy = {}
  let s:toas_run_reasoning_open = {}
  let s:toas_run_buffers = {}
  for l:run_id in keys(s:toas_run_timers)
    try
      call timer_stop(s:toas_run_timers[l:run_id])
    catch
    endtry
  endfor
  let s:toas_run_timers = {}
  let s:toas_run_data_pumps = {}
  let s:toas_run_metrics = {}
  let s:toas_run_watch_ticks = {}
  let s:toas_run_watch_interval = {}
  let s:toas_watch_debug = {}
  let s:toas_lane_health = {}
  let s:toas_step_counter = 0
  let g:toas_active_run_id = ''
  let g:toas_last_run_status = ''
endfunction

function! s:toas_host_on_stderr(...) abort
  if a:0 < 2
    return
  endif
  let l:data = a:2
  if type(l:data) != type([])
    return
  endif
  for l:line in l:data
    if type(l:line) == type('') && l:line !=# ''
      call add(s:toas_host_stderr_tail, l:line)
    endif
  endfor
  if len(s:toas_host_stderr_tail) > 40
    let s:toas_host_stderr_tail = s:toas_host_stderr_tail[-40:]
  endif
endfunction

function! s:toas_host_on_stdout(ch, msg) abort
  if type(a:msg) != type('') || a:msg ==# ''
    return
  endif
  let s:toas_host_rx_buffer .= a:msg
  " Channel-read-driven scheduling: wake active local_host watchers immediately.
  for l:run_id in keys(s:toas_watch_pump)
    let l:pump = s:toas_watch_pump[l:run_id]
    if type(l:pump) == type({}) && get(l:pump, 'phase', '') ==# 'harvest'
      call s:toas_schedule_data_pump(l:run_id)
    endif
  endfor
endfunction

function! s:toas_host_on_exit(...) abort
  if a:0 >= 2
    let s:toas_host_last_exit = a:2
    return
  endif
  if a:0 >= 1
    let s:toas_host_last_exit = a:1
  endif
endfunction

function! s:toas_host_job_handle_valid() abort
  if s:toas_host_job is v:null
    return 0
  endif
  if type(s:toas_host_job) == type(0)
    return s:toas_host_job > 0
  endif
  if type(s:toas_host_job) == type('')
    return s:toas_host_job !=# ''
  endif
  return 1
endfunction

function! s:toas_host_reset(reason) abort
  if exists('*job_stop') && s:toas_host_job_handle_valid()
    try
      call job_stop(s:toas_host_job)
    catch
    endtry
  endif
  let s:toas_host_job = -1
  let s:toas_host_channel = v:null
  let s:toas_host_rx_buffer = ''
  let s:toas_host_launch_transport = ''
endfunction

function! s:toas_system_in_workdir(cmd) abort
  let l:cwd_save = getcwd()
  try
    execute 'lcd! ' . fnameescape(s:toas_workdir())
    let l:out = system(a:cmd)
    let l:code = v:shell_error
  finally
    execute 'lcd! ' . fnameescape(l:cwd_save)
  endtry
  return {'stdout': l:out, 'exit_code': l:code}
endfunction

function! s:toas_owner_id() abort
  if exists('g:toas_owner_id') && type(g:toas_owner_id) == type('') && g:toas_owner_id !=# ''
    return g:toas_owner_id
  endif
  let l:server = exists('v:servername') && v:servername !=# '' ? v:servername : 'vim'
  return l:server . '-' . getpid()
endfunction

function! s:toas_set_owner_env() abort
  let $TOAS_OWNER_KIND = 'editor'
  let $TOAS_OWNER_ID = s:toas_owner_id()
endfunction

function! s:toas_host_ensure_started() abort
  if !exists('*job_start') || !exists('*job_status')
    return 0
  endif
  let l:target_transport = s:toas_transport_mode() ==# 'local_host' ? 'local_host' : 'rpc'
  if s:toas_host_job_handle_valid() && s:toas_host_launch_transport !=# '' && s:toas_host_launch_transport !=# l:target_transport
    call s:toas_host_reset('transport switch')
  endif
  if s:toas_host_job_handle_valid()
    try
      if job_status(s:toas_host_job) ==# 'run'
        if s:toas_transport_mode() ==# 'local_host' && exists('*job_getchannel')
          let l:deadline = reltimefloat(reltime()) + 1.0
          while reltimefloat(reltime()) < l:deadline
            let s:toas_host_channel = job_getchannel(s:toas_host_job)
            if s:toas_host_channel isnot v:null
              try
                call ch_setoptions(s:toas_host_channel, {'mode': 'raw'})
              catch
              endtry
              break
            endif
            sleep 20m
          endwhile
        endif
        return 1
      endif
    catch
    endtry
  endif
  call s:toas_set_owner_env()
  let l:cwd_save = getcwd()
  try
    execute 'lcd! ' . fnameescape(s:toas_workdir())
    let l:toas_cmd = executable('toas') ? ['toas'] : [exepath('python3'), '-m', 'toas.cli']
    if s:toas_transport_mode() ==# 'local_host'
      "let s:toas_host_start_cmd = l:toas_cmd + ['host', 'serve', '--owner-pid', string(getpid()), '--stdio-json']
      let s:toas_host_start_cmd = l:toas_cmd + ['host', 'serve', '--stdio-json']
      let s:toas_host_start_time = reltime()
      let s:toas_host_last_exit = v:null
      let s:toas_host_stderr_tail = []
      let s:toas_host_job = job_start(
            \ s:toas_host_start_cmd,
            \ {'in_io': 'pipe', 'out_io': 'pipe', 'out_mode': 'raw', 'out_cb': function('s:toas_host_on_stdout'), 'err_io': 'pipe', 'err_cb': function('s:toas_host_on_stderr'), 'exit_cb': function('s:toas_host_on_exit')}
            \ )
      let s:toas_host_launch_transport = 'local_host'
      if s:toas_host_job_handle_valid() && exists('*job_getchannel')
        let l:deadline = reltimefloat(reltime()) + 1.0
        while reltimefloat(reltime()) < l:deadline
          let s:toas_host_channel = job_getchannel(s:toas_host_job)
          if s:toas_host_channel isnot v:null
            try
              call ch_setoptions(s:toas_host_channel, {'mode': 'raw'})
            catch
            endtry
            break
          endif
          sleep 20m
        endwhile
      endif
    else
      let s:toas_host_start_cmd = l:toas_cmd + ['host', 'serve', '--owner-pid', string(getpid())]
      let s:toas_host_start_time = reltime()
      let s:toas_host_last_exit = v:null
      let s:toas_host_stderr_tail = []
      let s:toas_host_job = job_start(
            \ s:toas_host_start_cmd,
            \ {'in_io': 'null', 'out_io': 'null', 'err_io': 'pipe', 'err_cb': function('s:toas_host_on_stderr'), 'exit_cb': function('s:toas_host_on_exit')}
            \ )
      let s:toas_host_launch_transport = 'rpc'
    endif
  finally
    execute 'lcd! ' . fnameescape(l:cwd_save)
  endtry
  if s:toas_host_job_handle_valid() && exists('*job_status')
    let l:deadline = reltimefloat(reltime()) + 0.5
    while reltimefloat(reltime()) < l:deadline
      let l:status = job_status(s:toas_host_job)
      if l:status ==# 'run'
        break
      endif
      if l:status ==# 'dead'
        let g:toas_last_error = s:toas_host_fail_detail('host process died during startup')
        return 0
      endif
      sleep 20m
    endwhile
  endif
  if exists('*job_status') && s:toas_host_job_handle_valid() && job_status(s:toas_host_job) !=# 'run'
    let g:toas_last_error = s:toas_host_fail_detail('host process not running after startup wait')
    return 0
  endif
  return s:toas_host_job_handle_valid()
endfunction

function! s:toas_host_debug_state() abort
  let l:job_status = 'none'
  if exists('*job_status') && s:toas_host_job_handle_valid()
    try
      let l:job_status = job_status(s:toas_host_job)
    catch
      let l:job_status = 'error'
    endtry
  endif
  let l:channel_status = 'none'
  if exists('*ch_status') && s:toas_host_channel isnot v:null
    try
      let l:channel_status = ch_status(s:toas_host_channel)
    catch
      let l:channel_status = 'error'
    endtry
  endif
  let l:age_ms = -1
  if type(s:toas_host_start_time) == type(reltime())
    let l:age_ms = float2nr(reltimefloat(reltime(s:toas_host_start_time)) * 1000.0)
  endif
  return {
        \ 'transport_mode': s:toas_transport_mode(),
        \ 'host_job_id': s:toas_host_job,
        \ 'host_job_status': l:job_status,
        \ 'host_channel_status': l:channel_status,
        \ 'host_start_cmd': copy(s:toas_host_start_cmd),
        \ 'host_last_exit': s:toas_host_last_exit,
        \ 'host_start_age_ms': l:age_ms,
        \ 'host_stderr_tail': copy(s:toas_host_stderr_tail),
        \ }
endfunction

function! s:toas_host_pid() abort
  if !s:toas_host_job_handle_valid()
    return -1
  endif
  if exists('*job_info')
    try
      let l:info = job_info(s:toas_host_job)
      if type(l:info) == type({})
        if has_key(l:info, 'process') && type(l:info.process) == type(0) && l:info.process > 0
          return l:info.process
        endif
        if has_key(l:info, 'pid') && type(l:info.pid) == type(0) && l:info.pid > 0
          return l:info.pid
        endif
      endif
    catch
    endtry
  endif
  return -1
endfunction

function! s:toas_host_fail_detail(reason) abort
  let l:dbg = s:toas_host_debug_state()
  return a:reason . ' | cmd=' . string(get(l:dbg, 'host_start_cmd', []))
        \ . ' status=' . string(get(l:dbg, 'host_job_status', 'unknown'))
        \ . ' channel=' . string(get(l:dbg, 'host_channel_status', 'unknown'))
        \ . ' exit=' . string(get(l:dbg, 'host_last_exit', v:null))
        \ . ' stderr=' . string(get(l:dbg, 'host_stderr_tail', []))
endfunction

function! ToasHostStart() abort
  call s:toas_set_owner_env()
  let l:ok = s:toas_host_ensure_started()
  if l:ok
    call s:toas_notice('toas host start ok')
  else
    echoerr 'ToasHostStart failed: ' . get(g:, 'toas_last_error', 'unknown')
  endif
  echo string(s:toas_host_debug_state())
endfunction

function! s:toas_host_stop_on_exit() abort
  call s:toas_set_owner_env()
  call s:toas_system_in_workdir('toas host stop')
endfunction

function! ToasRestart() abort
  call s:toas_reset_runtime_state()

  let l:stop = s:toas_system_in_workdir('toas daemon stop')
  let l:start = s:toas_system_in_workdir('toas daemon start')
  let l:status = s:toas_system_in_workdir('toas daemon status')

  if l:start.exit_code !=# 0
    let g:toas_last_error = 'daemon restart failed: ' . substitute(l:start.stdout, '\n\+$', '', '')
    echoerr 'ToasRestart failed: ' . g:toas_last_error
    return
  endif

  let g:toas_last_error = ''
  let l:status_line = substitute(l:status.stdout, '\n\+$', '', '')
  if l:status_line ==# ''
    let l:status_line = 'daemon running'
  endif
  if l:stop.exit_code !=# 0
    call s:toas_notice('toas daemon restarted (stop best-effort): ' . l:status_line)
  else
    call s:toas_notice('toas daemon restarted: ' . l:status_line)
  endif
endfunction

function! ToasWatchDebug(...) abort
  let l:run_id = get(g:, 'toas_active_run_id', '')
  if a:0 >= 1 && a:1 !=# ''
    let l:run_id = a:1
  endif
  if l:run_id ==# '' || !has_key(s:toas_watch_debug, l:run_id)
    echo '{}'
    return
  endif
  echo string(s:toas_watch_debug[l:run_id])
endfunction

command! ToasStepHere call ToasStepHere()
nnoremap <leader>S :ToasStepHere<CR>
command! ToasStepAsync call ToasStepAsync()
command! -nargs=* ToasWatch call ToasWatch(<f-args>)
command! -nargs=? ToasCancel call ToasCancel(<f-args>)
command! ToasRestart call ToasRestart()
command! ToasResetState call <SID>toas_reset_runtime_state()
command! ToasHostDebug echo string(<SID>toas_host_debug_state())
command! ToasHostStart call ToasHostStart()
command! ToasHostPid echo <SID>toas_host_pid()
nnoremap <leader>x :ToasCancel<CR>
command! ToasTransport echo get(g:, 'toas_last_step_transport', '')
command! ToasLastError echo get(g:, 'toas_last_error', '')
command! ToasRpcLens echo 'raw=' . get(g:, 'toas_last_rpc_raw_len', -1) . ' stdout=' . get(g:, 'toas_last_rpc_stdout_len', -1)
command! ToasRunId echo get(g:, 'toas_active_run_id', '')
command! ToasRunStatus echo get(g:, 'toas_last_run_status', '')
command! ToasLane echo get(g:, 'toas_last_step_lane', '')
command! ToasFallback echo get(g:, 'toas_last_step_fallback_reason', '')
command! ToasTiming echo string(get(g:, 'toas_last_step_timing', {}))
command! ToasLaneHealth echo string(s:toas_lane_health)
command! -nargs=? ToasWatchDebug call ToasWatchDebug(<f-args>)
command! ToasDebug echo 'workdir=' . s:toas_workdir() . ' raw_g_toas_workdir=' . string(get(g:, 'toas_workdir', '')) . ' cwd=' . getcwd() . ' port_file=' . s:toas_vim_port_path() . ' readable=' . filereadable(s:toas_vim_port_path())
command! ToasProbe call <SID>ToasProbe()

call s:toas_set_owner_env()
augroup toas_owner_lifecycle
  autocmd!
  autocmd VimLeavePre * call <SID>toas_host_stop_on_exit()
augroup END

function! s:ToasProbe() abort
  let l:ok = s:toas_channel_open()
  echo 'ok=' . l:ok . ' addr=' . get(g:, 'toas_last_addr', '') . ' status=' . get(g:, 'toas_last_open_status', '')
endfunction
