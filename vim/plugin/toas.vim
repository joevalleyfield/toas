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
    echom printf('toas async run started: %s (%s)', l:run_id, l:status)
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
      echom printf('toas async run started: %s (running)', g:toas_active_run_id)
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
        echom printf('toas run %s: %s', l:run_id, l:status)
        break
      endif
      if !l:follow
        echom printf('toas run %s: %s', l:run_id, l:status)
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
    echom printf('toas run %s: %s', l:run_id, l:status)
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
