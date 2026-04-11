if exists('g:loaded_toas_plugin')
  finish
endif
let g:loaded_toas_plugin = 1

let s:toas_channel = v:null
let g:toas_last_step_transport = ''
let g:toas_last_error = ''
let g:toas_last_rpc_raw_len = -1
let g:toas_last_rpc_stdout_len = -1
let g:toas_active_run_id = ''
let g:toas_last_run_status = ''
let s:toas_watch_offset = {}
let s:toas_watch_seq = {}
let s:toas_run_text = {}
let s:toas_run_buffers = {}
let s:toas_run_timers = {}
if !exists('g:toas_step_nonblocking')
  let g:toas_step_nonblocking = 1
endif
if !exists('g:toas_notice_enabled')
  let g:toas_notice_enabled = 0
endif

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
    return fnamemodify(g:toas_workdir, ':p')
  endif
  let l:start = expand('%:p:h')
  if l:start ==# ''
    let l:start = getcwd()
  endif
  let l:session = findfile('session.md', l:start . ';')
  if l:session !=# ''
    return fnamemodify(l:session, ':p:h')
  endif
  return getcwd()
endfunction

function! s:toas_socket_path() abort
  if exists('g:toas_socket_path')
    return g:toas_socket_path
  endif
  return s:toas_workdir() . '/.toas.sock'
endfunction

function! s:toas_vim_port_path() abort
  if exists('g:toas_vim_port_path')
    return g:toas_vim_port_path
  endif
  let l:candidates = [
        \ s:toas_workdir() . '/.toas.vim-port',
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
  let l:resp = s:toas_rpc_request('step', {'workdir': s:toas_workdir()}, 5.0)
  return get(get(l:resp, 'payload', {}), 'stdout', '')
endfunction

function! s:toas_step_rpc_async_collect() abort
  let l:start = s:toas_rpc_request('step_async', {'workdir': s:toas_workdir()}, 5.0)
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
    let l:watch = s:toas_rpc_request('watch', l:watch_payload, 5.0)
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

function! s:toas_render_run_lines(run_id, status, text) abort
  let l:lines = [s:toas_run_marker_start(a:run_id), 'status: ' . a:status, '']
  if a:text !=# ''
    let l:body = split(substitute(a:text, '\r', '', 'g'), "\n", 1)
    call extend(l:lines, l:body)
  endif
  call add(l:lines, s:toas_run_marker_end(a:run_id))
  return l:lines
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
    let l:new_lines = s:toas_render_run_lines(a:run_id, a:status, a:text)
  else
    let l:new_lines = s:toas_render_run_body_lines(a:text)
  endif
  call s:toas_replace_buffer_region(l:bufnr, l:start, l:end, l:new_lines)
  return 1
endfunction

function! s:toas_insert_run_region(run_id, status, insert_after) abort
  let l:bufnr = bufnr('%')
  let l:view = winsaveview()
  let l:lines = s:toas_render_run_lines(a:run_id, a:status, '')
  call append(a:insert_after, l:lines)
  call winrestview(l:view)
  let s:toas_run_buffers[a:run_id] = l:bufnr
  return 1
endfunction

function! s:toas_stop_run_watcher(run_id) abort
  if has_key(s:toas_run_timers, a:run_id)
    call timer_stop(s:toas_run_timers[a:run_id])
    call remove(s:toas_run_timers, a:run_id)
  endif
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
        \ }
  try
    let l:resp = s:toas_rpc_request('watch', l:payload, 5.0)
    let l:data = get(l:resp, 'payload', {})
    let l:chunk = get(l:data, 'chunk', '')
    if !has_key(s:toas_run_text, a:run_id)
      let s:toas_run_text[a:run_id] = ''
    endif
    if l:chunk !=# ''
      let s:toas_run_text[a:run_id] = s:toas_apply_chunk_with_carriage(
            \ s:toas_run_text[a:run_id],
            \ l:chunk,
            \ )
    endif
    let s:toas_watch_offset[a:run_id] = get(l:data, 'next_offset', get(s:toas_watch_offset, a:run_id, 0))
    let s:toas_watch_seq[a:run_id] = get(l:data, 'next_seq', get(s:toas_watch_seq, a:run_id, 0))
    let l:status = get(l:data, 'status', 'running')
    let g:toas_last_run_status = l:status
    let g:toas_active_run_id = a:run_id
    call s:toas_replace_run_region(a:run_id, l:status, get(s:toas_run_text, a:run_id, ''), 1)
    if l:status ==# 'succeeded' || l:status ==# 'failed' || l:status ==# 'cancelled'
      if l:status ==# 'succeeded'
        " Successful completion drops sentinel markers and keeps canonical projection blocks only.
        let l:final_text = s:toas_extract_final_projection(get(s:toas_run_text, a:run_id, ''))
        call s:toas_replace_run_region(a:run_id, l:status, l:final_text, 0)
      endif
      call s:toas_stop_run_watcher(a:run_id)
      call s:toas_notice(printf('toas run %s: %s', a:run_id, l:status))
    endif
  catch
    let g:toas_last_error = v:exception
    call s:toas_stop_run_watcher(a:run_id)
    call s:toas_notice('toas watcher error: ' . g:toas_last_error)
  endtry
endfunction

function! s:toas_start_nonblocking_step(insert_after) abort
  if !exists('*timer_start')
    throw 'timer support unavailable'
  endif
  let l:resp = s:toas_rpc_request('step_async', {'workdir': s:toas_workdir()}, 5.0)
  let l:payload = get(l:resp, 'payload', {})
  let l:run_id = get(l:payload, 'run_id', '')
  let l:status = get(l:payload, 'status', 'running')
  if l:run_id ==# ''
    throw 'missing run_id in step_async response'
  endif
  let g:toas_active_run_id = l:run_id
  let g:toas_last_run_status = l:status
  let s:toas_watch_offset[l:run_id] = 0
  let s:toas_watch_seq[l:run_id] = 0
  let s:toas_run_text[l:run_id] = ''
  call s:toas_insert_run_region(l:run_id, l:status, a:insert_after)
  let l:timer = timer_start(120, function('s:toas_watch_tick', [l:run_id]), {'repeat': -1})
  let s:toas_run_timers[l:run_id] = l:timer
  return l:run_id
endfunction

function! s:toas_rpc_request(op, payload, timeout_s) abort
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

function! ToasStep() abort
  " ensure disk is current
  if &modified
    write
  endif

  if get(g:, 'toas_step_nonblocking', 0) && exists('*timer_start')
    try
      " Step evaluates frontier at tail; keep async insertion anchored to tail as well.
      let l:run_id = s:toas_start_nonblocking_step(line('$'))
      let g:toas_last_step_transport = 'rpc_async_nonblocking'
      let g:toas_last_error = ''
      call s:toas_notice(printf('toas async run started: %s', l:run_id))
      return
    catch
      let g:toas_last_error = v:exception
    endtry
  endif

  " try daemon first
  try
    let l:out = s:toas_step_rpc_async_collect()
    let g:toas_last_step_transport = 'rpc_async'
    let g:toas_last_error = ''
    if l:out !=# ''
      call append(line('$'), split(substitute(l:out, '\r', '', 'g'), "\n"))
      normal! G
    endif
    return
  catch
    let g:toas_last_error = v:exception
  endtry

  " fallback: sync RPC
  try
    let l:out = s:toas_step_rpc()
    let g:toas_last_step_transport = 'rpc'
    let g:toas_last_error = ''
    if l:out !=# ''
      call append(line('$'), split(substitute(l:out, '\r', '', 'g'), "\n"))
      normal! G
    endif
    return
  catch
    let g:toas_last_error = v:exception
    let s:toas_channel = v:null
  endtry

  " fallback: CLI
  let g:toas_last_step_transport = 'cli_fallback'
  let l:cwd_save = getcwd()
  try
    execute 'lcd ' . fnameescape(s:toas_workdir())
    let l:out = system('toas step')
  finally
    execute 'lcd ' . fnameescape(l:cwd_save)
  endtry
  call append(line('$'), split(substitute(l:out, '\r', '', 'g'), "\n"))
  normal! G
endfunction

command! ToasStep call ToasStep()
nnoremap <leader>s :ToasStep<CR>

function! ToasStepAsync() abort
  if &modified
    write
  endif

  try
    let l:resp = s:toas_rpc_request('step_async', {'workdir': s:toas_workdir()}, 5.0)
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
    let g:toas_last_step_transport = 'rpc'
    let g:toas_last_error = ''
    call s:toas_notice(printf('toas async run started: %s (%s)', l:run_id, l:status))
  catch
    let g:toas_last_error = v:exception
    let s:toas_channel = v:null
    let g:toas_last_step_transport = 'cli_fallback'
    let l:cwd_save = getcwd()
    try
      execute 'lcd ' . fnameescape(s:toas_workdir())
      let l:out = system('toas step --async')
    finally
      execute 'lcd ' . fnameescape(l:cwd_save)
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

  while 1
    let l:payload = {
          \ 'workdir': s:toas_workdir(),
          \ 'run_id': l:run_id,
          \ 'offset': get(s:toas_watch_offset, l:run_id, 0),
          \ 'since_seq': get(s:toas_watch_seq, l:run_id, 0),
          \ }
    try
      let l:resp = s:toas_rpc_request('watch', l:payload, 5.0)
      let l:data = get(l:resp, 'payload', {})
      let l:chunk = get(l:data, 'chunk', '')
      if l:chunk !=# ''
        call append(line('$'), split(substitute(l:chunk, '\r', '', 'g'), "\n"))
        normal! G
      endif
      let s:toas_watch_offset[l:run_id] = get(l:data, 'next_offset', get(s:toas_watch_offset, l:run_id, 0))
      let s:toas_watch_seq[l:run_id] = get(l:data, 'next_seq', get(s:toas_watch_seq, l:run_id, 0))
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
    let l:resp = s:toas_rpc_request('cancel', {'workdir': s:toas_workdir(), 'run_id': l:run_id}, 5.0)
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
      let l:run_id = s:toas_start_nonblocking_step(line('$'))
      let g:toas_last_step_transport = 'rpc_async_nonblocking'
      let g:toas_last_error = ''
      " reattach tail immediately; stream writes stay in sentinel run region.
      if !empty(l:tail)
        call append(line('$'), l:tail)
      endif
      call s:toas_notice(printf('toas async run started: %s', l:run_id))
      return
    catch
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
      let s:toas_channel = v:null
      let g:toas_last_step_transport = 'cli_fallback'
      let l:cwd_save = getcwd()
      try
        execute 'lcd ' . fnameescape(s:toas_workdir())
        let l:out = system('toas step')
      finally
        execute 'lcd ' . fnameescape(l:cwd_save)
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

command! ToasStepHere call ToasStepHere()
nnoremap <leader>S :ToasStepHere<CR>
command! ToasStepAsync call ToasStepAsync()
command! -nargs=* ToasWatch call ToasWatch(<f-args>)
command! -nargs=? ToasCancel call ToasCancel(<f-args>)
nnoremap <leader>x :ToasCancel<CR>
command! ToasTransport echo get(g:, 'toas_last_step_transport', '')
command! ToasLastError echo get(g:, 'toas_last_error', '')
command! ToasRpcLens echo 'raw=' . get(g:, 'toas_last_rpc_raw_len', -1) . ' stdout=' . get(g:, 'toas_last_rpc_stdout_len', -1)
command! ToasRunId echo get(g:, 'toas_active_run_id', '')
command! ToasRunStatus echo get(g:, 'toas_last_run_status', '')
command! ToasDebug echo 'workdir=' . s:toas_workdir() . ' port_file=' . s:toas_vim_port_path() . ' readable=' . filereadable(s:toas_vim_port_path())
command! ToasProbe call <SID>ToasProbe()

function! s:ToasProbe() abort
  let l:ok = s:toas_channel_open()
  echo 'ok=' . l:ok . ' addr=' . get(g:, 'toas_last_addr', '') . ' status=' . get(g:, 'toas_last_open_status', '')
endfunction
