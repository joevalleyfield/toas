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
let s:toas_run_stream_policy = {}
let s:toas_run_buffers = {}
let s:toas_run_timers = {}
let s:toas_run_metrics = {}
let s:toas_lane_health = {}
let s:toas_step_counter = 0
let s:toas_run_watch_ticks = {}
let s:toas_run_watch_interval = {}
let s:toas_watch_debug = {}
let s:toas_host_job = -1
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
  let g:toas_transport_mode = 'rpc'
endif
if !exists('g:toas_local_host_debug_single_lane')
  let g:toas_local_host_debug_single_lane = 1
endif
if !exists('g:toas_local_host_wire_log')
  let g:toas_local_host_wire_log = 1
endif

function! s:toas_wire_log(msg) abort
  if !get(g:, 'toas_local_host_wire_log', 0)
    return
  endif
  let l:path = s:toas_workdir() . '/.toas/host-stdio-vim.log'
  call mkdir(fnamemodify(l:path, ':h'), 'p')
  call writefile([strftime('%Y-%m-%dT%H:%M:%S') . ' ' . a:msg], l:path, 'a')
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

function! s:toas_workdir() abort
  if exists('g:toas_workdir') && type(g:toas_workdir) == type('') && g:toas_workdir !=# ''
    let l:resolved = fnamemodify(g:toas_workdir, ':p')
    if has('win32') || has('win64')
      return substitute(l:resolved, '^\/\([a-zA-Z]\)\/', '\1:\/', '')
    endif
    return l:resolved
  endif

  let l:start = expand('%:p:h')
  if l:start ==# ''
    let l:start = getcwd()
  endif
  let l:cmd = 'cd ' . shellescape(l:start) . ' && toas session-path'
  let l:raw = trim(system(l:cmd))
  if v:shell_error == 0 && l:raw !=# ''
    let l:session_path = fnamemodify(l:raw, ':p')
    let l:normalized = substitute(l:session_path, '[\/]\.toas[\/].*$', '', '')
    if l:normalized !=# l:session_path && l:normalized !=# ''
      let l:resolved = l:normalized
    else
      let l:resolved = fnamemodify(l:session_path, ':h')
    endif
    if has('win32') || has('win64')
      return substitute(l:resolved, '^\/\([a-zA-Z]\)\/', '\1:\/', '')
    endif
    return l:resolved
  endif

  let l:fallback = getcwd()
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
    return 0
  endif
  call s:toas_replace_buffer_region(l:bufnr, l:start, l:end, l:new_lines)
  return 1
endfunction

function! s:toas_insert_run_region(run_id, status, insert_after) abort
  let l:bufnr = bufnr('%')
  let l:view = winsaveview()
  let l:lines = s:toas_render_run_lines(a:run_id, a:status, '', '')
  call append(a:insert_after, l:lines)
  call winrestview(l:view)
  let s:toas_run_buffers[a:run_id] = l:bufnr
  let s:toas_run_status[a:run_id] = a:status
  let s:toas_run_progress[a:run_id] = ''
  return 1
endfunction

function! s:toas_stop_run_watcher(run_id) abort
  if has_key(s:toas_run_timers, a:run_id)
    call timer_stop(s:toas_run_timers[a:run_id])
    call remove(s:toas_run_timers, a:run_id)
  endif
  if has_key(s:toas_run_watch_ticks, a:run_id)
    call remove(s:toas_run_watch_ticks, a:run_id)
  endif
  if has_key(s:toas_run_watch_interval, a:run_id)
    call remove(s:toas_run_watch_interval, a:run_id)
  endif
endfunction

function! s:toas_watch_debug_update(run_id, status, chunk_len, next_offset, next_seq, redraw) abort
  if !has_key(s:toas_watch_debug, a:run_id)
    let s:toas_watch_debug[a:run_id] = {
          \ 'ticks': 0,
          \ 'redraws': 0,
          \ 'bytes_seen': 0,
          \ 'max_chunk_len': 0,
          \ 'history': [],
          \ 'last': {},
          \ }
  endif
  let s:toas_watch_debug[a:run_id].ticks += 1
  let s:toas_watch_debug[a:run_id].bytes_seen += a:chunk_len
  if a:chunk_len > get(s:toas_watch_debug[a:run_id], 'max_chunk_len', 0)
    let s:toas_watch_debug[a:run_id].max_chunk_len = a:chunk_len
  endif
  if a:redraw
    let s:toas_watch_debug[a:run_id].redraws += 1
  endif
  call add(s:toas_watch_debug[a:run_id].history, {
        \ 'status': a:status,
        \ 'chunk_len': a:chunk_len,
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
  if !has_key(s:toas_run_buffers, a:run_id)
    call s:toas_stop_run_watcher(a:run_id)
    return
  endif
  let l:bufnr = s:toas_run_buffers[a:run_id]
  if !bufexists(l:bufnr) || !bufloaded(l:bufnr)
    call s:toas_stop_run_watcher(a:run_id)
    return
  endif
  let l:region = s:toas_find_run_region(l:bufnr, a:run_id)
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
    let l:resp = s:toas_request('watch', l:payload, 5.0)
    let s:toas_run_watch_ticks[a:run_id] = get(s:toas_run_watch_ticks, a:run_id, 0) + 1
    if get(s:toas_run_watch_ticks, a:run_id, 0) >= 5 && get(s:toas_run_watch_interval, a:run_id, 20) != 100
      if has_key(s:toas_run_timers, a:run_id)
        call timer_stop(s:toas_run_timers[a:run_id])
      endif
      let s:toas_run_timers[a:run_id] = timer_start(100, function('s:toas_watch_tick', [a:run_id]), {'repeat': -1})
      let s:toas_run_watch_interval[a:run_id] = 100
      if has_key(s:toas_run_metrics, a:run_id)
        let s:toas_run_metrics[a:run_id].watch_steady_ms = 100
      endif
    endif
    let l:data = get(l:resp, 'payload', {})
    let l:chunk = get(l:data, 'chunk', '')
    let l:error = get(l:data, 'error', '')
    let l:events = get(l:data, 'events', [])
    let l:stream_policy = get(l:data, 'stream_policy', {})
    if type(l:stream_policy) == type({})
      let s:toas_run_stream_policy[a:run_id] = l:stream_policy
    endif
    if !has_key(s:toas_run_text, a:run_id)
      let s:toas_run_text[a:run_id] = ''
    endif
    if type(l:events) == type([])
      for l:event in l:events
        if type(l:event) != type({})
          continue
        endif
        if get(l:event, 'type', '') ==# 'prompt_progress'
          let l:progress_text = s:toas_format_progress_event(get(l:event, 'payload', {}))
          if l:progress_text !=# ''
            let s:toas_run_progress[a:run_id] = l:progress_text
          endif
        endif
      endfor
    endif
    if l:chunk !=# ''
      let s:toas_run_text[a:run_id] = s:toas_apply_chunk_with_carriage(
            \ s:toas_run_text[a:run_id],
            \ l:chunk,
            \ )
      let l:progress_from_text = s:toas_extract_prompt_progress(s:toas_run_text[a:run_id])
      if l:progress_from_text !=# ''
        let s:toas_run_progress[a:run_id] = l:progress_from_text
      endif
    endif
    let s:toas_watch_offset[a:run_id] = get(l:data, 'next_offset', get(s:toas_watch_offset, a:run_id, 0))
    let s:toas_watch_seq[a:run_id] = get(l:data, 'next_seq', get(s:toas_watch_seq, a:run_id, 0))
    let l:status = get(l:data, 'status', 'running')
    let l:previous_status = get(s:toas_run_status, a:run_id, '')
    let s:toas_run_status[a:run_id] = l:status
    let g:toas_last_run_status = l:status
    let g:toas_active_run_id = a:run_id
    let l:redraw = v:false
    if l:chunk !=# '' || l:status !=# l:previous_status
      if (l:status ==# 'failed' || l:status ==# 'cancelled') && l:error !=# '' && get(s:toas_run_text, a:run_id, '') ==# ''
        let s:toas_run_text[a:run_id] = '[run ' . l:status . '] ' . l:error . "\n"
      endif
      call s:toas_replace_run_region(a:run_id, l:status, get(s:toas_run_text, a:run_id, ''), 1)
      let l:redraw = v:true
    endif
    call s:toas_watch_debug_update(a:run_id, l:status, strlen(l:chunk), get(l:data, 'next_offset', -1), get(l:data, 'next_seq', -1), l:redraw)
    if l:status ==# 'succeeded' || l:status ==# 'failed' || l:status ==# 'cancelled'
      let s:toas_run_progress[a:run_id] = ''
      if l:status ==# 'succeeded'
        " Successful completion drops sentinel markers and keeps canonical projection blocks only.
        let l:final_text = s:toas_extract_final_projection(get(s:toas_run_text, a:run_id, ''))
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
      call s:toas_notice(printf('toas run %s: %s', a:run_id, l:status))
    endif
  catch
    let g:toas_last_error = v:exception
    call s:toas_stop_run_watcher(a:run_id)
    call s:toas_notice('toas watcher error: ' . g:toas_last_error)
  endtry
endfunction

function! s:toas_start_nonblocking_step(insert_after, op_name, lane_name) abort
  if !exists('*timer_start')
    throw 'timer support unavailable'
  endif
  let l:start = reltime()
  let l:resp = s:toas_request(a:op_name, {'workdir': s:toas_workdir()}, 15.0)
  let l:payload = get(l:resp, 'payload', {})
  let l:run_id = get(l:payload, 'run_id', '')
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
  let s:toas_run_stream_policy[l:run_id] = l:stream_policy
  let s:toas_run_watch_ticks[l:run_id] = 0
  let s:toas_run_watch_interval[l:run_id] = 20
  let s:toas_run_metrics[l:run_id] = {
        \ 'lane': a:lane_name,
        \ 'step_async_op': a:op_name,
        \ 'step_async_rpc_ms': s:toas_ms_since(l:start),
        \ 'watch_initial_ms': 20,
        \ 'watch_steady_ms': 100,
        \ 'start_reltime': reltime(),
        \ }
  call s:toas_insert_run_region(l:run_id, l:status, a:insert_after)
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
  let l:mode = get(g:, 'toas_transport_mode', 'rpc')
  if type(l:mode) != type('')
    return 'rpc'
  endif
  let l:mode = tolower(trim(l:mode))
  if l:mode ==# 'rpc_local_backend'
    return 'rpc_local_backend'
  endif
  if l:mode ==# 'local_host'
    return 'local_host'
  endif
  return 'rpc'
endfunction

function! s:toas_request_payload(op, payload) abort
  let l:out = copy(a:payload)
  if s:toas_transport_mode() ==# 'rpc_local_backend' || s:toas_transport_mode() ==# 'local_host'
    if a:op ==# 'step_async' || a:op ==# 'step_async_warm' || a:op ==# 'step_async_cold' || a:op ==# 'watch' || a:op ==# 'cancel'
      let l:out.backend_mode = 'local'
    endif
  endif
  return l:out
endfunction

function! s:toas_request(op, payload, timeout_s) abort
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
    call ch_sendraw(s:toas_host_channel, json_encode(l:req) . "\n")
    let l:deadline = reltimefloat(reltime()) + a:timeout_s
    while reltimefloat(reltime()) < l:deadline
      let l:norm = substitute(s:toas_host_rx_buffer, "\%x00", "\n", 'g')
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
            if type(l:parsed) == type({})
              call s:toas_wire_log('RECV request_id=' . string(get(l:parsed, 'request_id', '')) . ' ok=' . string(get(l:parsed, 'ok', v:false)))
              let l:last_parsed = l:parsed
              if get(l:parsed, 'request_id', '') ==# l:expect_id
                let l:resp = l:parsed
                break
              endif
            endif
          catch
            " Ignore undecodable partials and continue accumulating.
          endtry
        endfor
        if l:resp isnot v:null
          break
        endif
      endif

      let l:chunk = ch_readraw(s:toas_host_channel, {'timeout': 250})
      if type(l:chunk) == type('') && l:chunk !=# ''
        let s:toas_host_rx_buffer .= l:chunk
      endif
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

  let l:req = {
        \ 'protocol_version': 1,
        \ 'request_id': s:toas_request_id(),
        \ 'op': 'stream_subscribe',
        \ 'payload': {'run_id': a:run_id, 'timeout_s': a:timeout_s},
        \ }
  let l:frames = []
  call ch_sendraw(s:toas_host_channel, json_encode(l:req) . "\n")
  let l:deadline = reltimefloat(reltime()) + a:timeout_s + 1.0
  while reltimefloat(reltime()) < l:deadline
    let l:norm = substitute(s:toas_host_rx_buffer, "\%x00", "\n", 'g')
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
          if l:kind ==# 'push_complete'
            return l:frames
          endif
        catch
          " Ignore undecodable or partial frames.
        endtry
      endfor
    endif
    let l:chunk = ch_readraw(s:toas_host_channel, {'timeout': 200})
    if type(l:chunk) == type('') && l:chunk !=# ''
      let s:toas_host_rx_buffer .= l:chunk
    endif
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

function! s:toas_try_step_lane(lane, insert_after) abort
  if a:lane ==# 'default'
    if !get(g:, 'toas_step_nonblocking', 0) || !exists('*timer_start')
      throw 'default lane unavailable: nonblocking timer path disabled'
    endif
    let l:run_id = s:toas_start_nonblocking_step(a:insert_after, 'step_async', 'default')
    let g:toas_last_step_transport = 'rpc_async_nonblocking'
    return {'kind': 'async_started', 'run_id': l:run_id}
  endif

  if a:lane ==# 'warm'
    if !get(g:, 'toas_step_nonblocking', 0) || !exists('*timer_start')
      throw 'warm lane unavailable: nonblocking timer path disabled'
    endif
    let l:run_id = s:toas_start_nonblocking_step(a:insert_after, 'step_async_warm', 'warm')
    let g:toas_last_step_transport = 'rpc_async_nonblocking'
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

  for l:lane in s:toas_lane_order()
    if !s:toas_lane_usable(l:lane)
      let l:state = s:toas_lane_state(l:lane)
      call add(l:fallbacks, printf('%s: cooling down until step %d', l:lane, get(l:state, 'cooldown_until_step', 0)))
      continue
    endif
    try
      let l:result = s:toas_try_step_lane(l:lane, line('$'))
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
      call s:toas_note_lane_failure(l:lane, v:exception)
      call add(l:fallbacks, printf('%s: %s', l:lane, v:exception))
      let g:toas_last_error = v:exception
    endtry
  endfor

  " unreachable in normal policy because synchronous lane includes CLI fallback.
  call s:toas_record_lane('none', join(l:fallbacks, ' | '))
  if s:toas_transport_mode() ==# 'local_host'
    let g:toas_last_step_transport = 'local_host_error'
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
        let l:frames = s:toas_local_host_subscribe_frames(l:run_id, 5.0)
        for l:frame in l:frames
          let l:pl = get(l:frame, 'payload', {})
          let l:kind = get(l:pl, 'kind', '')
          if l:kind ==# 'push_event'
            let l:event = get(l:pl, 'event', {})
            if get(l:event, 'type', '') ==# 'llm_delta'
              let l:text = get(get(l:event, 'payload', {}), 'text', '')
              if l:text !=# ''
                call append(line('$'), split(substitute(l:text, '\r', '', 'g'), "\n"))
                normal! G
              endif
            elseif get(l:event, 'type', '') ==# 'llm_done'
              let l:status = get(get(l:event, 'payload', {}), 'status', '')
              if l:status !=# ''
                let g:toas_last_run_status = l:status
              endif
            endif
          elseif l:kind ==# 'push_complete'
            let l:complete = get(l:pl, 'complete', v:false)
            if l:complete == v:true && g:toas_last_run_status ==# ''
              let g:toas_last_run_status = 'succeeded'
            endif
          endif
        endfor
        let g:toas_active_run_id = l:run_id
        call s:toas_notice(printf('toas run %s: %s', l:run_id, g:toas_last_run_status ==# '' ? 'running' : g:toas_last_run_status))
        break
      catch
        " Fallback to compatibility watch polling when subscribe channel path is unavailable.
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
      let l:chunk = get(l:data, 'chunk', '')
      if l:chunk !=# ''
        call append(line('$'), split(substitute(l:chunk, '\r', '', 'g'), "\n"))
        normal! G
      endif
      if l:use_local_cursor
        let l:local_offset = get(l:data, 'next_offset', l:local_offset)
        let l:local_seq = get(l:data, 'next_seq', l:local_seq)
      else
        let s:toas_watch_offset[l:run_id] = get(l:data, 'next_offset', get(s:toas_watch_offset, l:run_id, 0))
        let s:toas_watch_seq[l:run_id] = get(l:data, 'next_seq', get(s:toas_watch_seq, l:run_id, 0))
      endif
      let l:status = get(l:data, 'status', '')
      let g:toas_last_run_status = l:status
      let g:toas_active_run_id = l:run_id
      if l:status ==# 'succeeded' || l:status ==# 'failed' || l:status ==# 'cancelled'
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
  if a:0 >= 1 && a:1 !=# ''
    let l:run_id = a:1
  endif
  if l:run_id ==# ''
    echoerr 'ToasCancel requires run_id or g:toas_active_run_id'
    return
  endif
  try
    let l:resp = s:toas_request('cancel', {'workdir': s:toas_workdir(), 'run_id': l:run_id}, 15.0)
    let l:data = get(l:resp, 'payload', {})
    let l:status = get(l:data, 'status', '')
    let g:toas_last_run_status = l:status
    let g:toas_active_run_id = l:run_id
    call s:toas_notice(printf('toas run %s: %s', l:run_id, l:status))
  catch
    let g:toas_last_error = v:exception
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
  let s:toas_watch_offset = {}
  let s:toas_watch_seq = {}
  let s:toas_run_text = {}
  let s:toas_run_progress = {}
  let s:toas_run_status = {}
  let s:toas_run_stream_policy = {}
  let s:toas_run_buffers = {}
  for l:run_id in keys(s:toas_run_timers)
    try
      call timer_stop(s:toas_run_timers[l:run_id])
    catch
    endtry
  endfor
  let s:toas_run_timers = {}
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
      let s:toas_host_start_cmd = l:toas_cmd + ['host', 'serve', '--owner-pid', string(getpid()), '--stdio-json']
      let s:toas_host_start_time = reltime()
      let s:toas_host_last_exit = v:null
      let s:toas_host_stderr_tail = []
      let s:toas_host_job = job_start(
            \ s:toas_host_start_cmd,
            \ {'in_io': 'pipe', 'out_io': 'pipe', 'err_io': 'pipe', 'err_cb': function('s:toas_host_on_stderr'), 'exit_cb': function('s:toas_host_on_exit')}
            \ )
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
command! ToasDebug echo 'workdir=' . s:toas_workdir() . ' port_file=' . s:toas_vim_port_path() . ' readable=' . filereadable(s:toas_vim_port_path())
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
