if exists('g:loaded_toas_stdio_contract')
  finish
endif
let g:loaded_toas_stdio_contract = 1

if !exists('g:toas_stdio_contract_host')
  let g:toas_stdio_contract_host = 'python3 tests/vim/stdio_contract_host_service.py'
endif

let s:sc_job = v:null
let s:sc_ch = v:null
let s:sc_rx = ''
let s:sc_frames = []
let s:sc_last_run = {}
let s:sc_bufnr = -1
let s:sc_timer = v:null
let s:sc_run = {}
let s:sc_pump_busy = 0
let s:sc_region_begin = '# BEGIN STREAM'
let s:sc_region_end = '# END STREAM'

function! s:sc_wirelog(msg) abort
  let l:path = get(g:, 'toas_stdio_contract_wirelog', '')
  if type(l:path) != type('') || l:path ==# ''
    return
  endif
  call writefile([printf('%s %s', strftime('%Y-%m-%dT%H:%M:%S'), a:msg)], l:path, 'a')
endfunction

function! s:sc_ensure_buffer() abort
  if s:sc_bufnr > 0 && bufexists(s:sc_bufnr)
    return s:sc_bufnr
  endif
  botright new
  setlocal buftype=nofile bufhidden=wipe noswapfile nobuflisted
  file [toas-stdio-contract]
  let s:sc_bufnr = bufnr('%')
  return s:sc_bufnr
endfunction

function! s:sc_init_buffer(scenario, host_speed) abort
  call s:sc_ensure_buffer()
  call deletebufline(s:sc_bufnr, 1, '$')
  call setbufline(s:sc_bufnr, 1, [
        \ '# TOAS STDIO CONTRACT',
        \ '',
        \ 'scenario: ' . a:scenario,
        \ 'host_speed: ' . a:host_speed,
        \ 'status: running (async)',
        \ '',
        \ s:sc_region_begin,
        \ s:sc_region_end,
        \ ])
endfunction

function! s:sc_region_bounds() abort
  let l:lines = getbufline(s:sc_bufnr, 1, '$')
  let l:b = 0
  let l:e = 0
  let l:i = 1
  for l:ln in l:lines
    if l:ln ==# s:sc_region_begin
      let l:b = l:i
    elseif l:ln ==# s:sc_region_end
      let l:e = l:i
      break
    endif
    let l:i += 1
  endfor
  if l:b == 0 || l:e == 0 || l:e <= l:b
    call setbufline(s:sc_bufnr, '$', [s:sc_region_begin, s:sc_region_end])
    let l:last = len(getbufline(s:sc_bufnr, 1, '$'))
    return [l:last - 1, l:last]
  endif
  return [l:b, l:e]
endfunction

function! s:sc_render_text(text) abort
  call s:sc_ensure_buffer()
  let [l:b, l:e] = s:sc_region_bounds()
  let l:body = split(a:text, "\n", 1)
  if !empty(l:body) && l:body[-1] ==# ''
    call remove(l:body, -1)
  endif
  if empty(l:body)
    let l:body = ['']
  endif
  call deletebufline(s:sc_bufnr, l:b + 1, l:e - 1)
  call appendbufline(s:sc_bufnr, l:b, l:body)
endfunction

function! s:sc_start() abort
  if type(s:sc_job) != type(v:null) && job_status(s:sc_job) ==# 'run' && type(s:sc_ch) != type(v:null) && ch_status(s:sc_ch) ==# 'open'
    return 1
  endif
  let l:cmd = split(g:toas_stdio_contract_host)
  let s:sc_job = job_start(l:cmd, {
        \ 'in_io': 'pipe',
        \ 'out_io': 'pipe',
        \ 'err_io': 'pipe',
        \ 'out_mode': 'raw',
        \ 'err_mode': 'raw',
        \ 'out_cb': function('s:sc_on_out'),
        \ 'err_cb': function('s:sc_on_err'),
        \ })
  let s:sc_ch = job_getchannel(s:sc_job)
  call ch_setoptions(s:sc_ch, {'mode': 'raw'})
  let s:sc_rx = ''
  let s:sc_frames = []
  return (type(s:sc_job) != type(v:null) && type(s:sc_ch) != type(v:null))
endfunction

function! s:sc_stop() abort
  if type(s:sc_timer) != type(v:null)
    call timer_stop(s:sc_timer)
    let s:sc_timer = v:null
  endif
  if type(s:sc_job) != type(v:null)
    call job_stop(s:sc_job)
  endif
  let s:sc_job = v:null
  let s:sc_ch = v:null
  let s:sc_rx = ''
  let s:sc_frames = []
  let s:sc_run = {}
endfunction

function! s:sc_on_out(ch, msg) abort
  if type(a:msg) != type('') || a:msg ==# ''
    return
  endif
  let l:chunk = substitute(a:msg, "\x00", "", 'g')
  call s:sc_wirelog('OUTCB len=' . strlen(l:chunk) . ' chunk=' . string(l:chunk))
  let s:sc_rx .= l:chunk
endfunction

function! s:sc_on_err(ch, msg) abort
  if type(a:msg) == type('') && a:msg !=# ''
    call s:sc_wirelog('ERRCB ' . string(a:msg))
  endif
endfunction

function! s:sc_decode_from_rx() abort
  let l:decoded = 0
  let l:max_decode = get(g:, 'toas_stdio_contract_decode_budget', 64)
  while l:decoded < l:max_decode && stridx(s:sc_rx, "\n") >= 0
    let l:line = split(s:sc_rx, "\n", 1)[0]
    let s:sc_rx = strpart(s:sc_rx, strlen(l:line) + 1)
    call s:sc_wirelog('LINE len=' . strlen(l:line) . ' head=' . string(strpart(l:line, 0, 80)))
    if l:line ==# ''
      continue
    endif
    try
      call add(s:sc_frames, json_decode(l:line))
      call s:sc_wirelog('PARSE ok')
    catch
      call s:sc_wirelog('PARSE error=' . v:exception)
      call add(s:sc_frames, {'ok': v:false, 'payload': {'kind': 'parse_error', 'line': l:line}})
    endtry
    let l:decoded += 1
  endwhile
endfunction

function! s:sc_tick(timer) abort
  if s:sc_pump_busy || empty(s:sc_run)
    return
  endif
  let s:sc_pump_busy = 1
  try
    call s:sc_decode_from_rx()

    for l:f in s:sc_frames
      let l:p = get(l:f, 'payload', {})
      if get(l:p, 'kind', '') ==# 'push_complete'
        let s:sc_run.complete = get(l:p, 'complete', v:false)
        break
      endif
    endfor

    let l:frame_budget = get(g:, 'toas_stdio_contract_frame_budget', 24)
    let l:processed = 0
    let l:remaining = []
    for l:f in s:sc_frames
      if l:processed >= l:frame_budget
        call add(l:remaining, l:f)
        continue
      endif
      let l:processed += 1
      let l:p = get(l:f, 'payload', {})
      let l:k = get(l:p, 'kind', '')
      if l:k !=# ''
        call add(s:sc_run.kinds, l:k)
      endif
      if l:k ==# 'push_event'
        let s:sc_run.text .= get(l:p, 'chunk', '')
      elseif l:k ==# 'parse_error'
        call add(s:sc_run.parse_errors, get(l:p, 'line', ''))
      endif
    endfor
    let s:sc_frames = l:remaining

    call s:sc_render_text(s:sc_run.text)
    if !empty(s:sc_run.parse_errors)
      let l:last = len(getbufline(s:sc_bufnr, 1, '$'))
      call setbufline(s:sc_bufnr, l:last + 1, ['', '[parse_error] ' . s:sc_run.parse_errors[-1]])
    endif

    if get(s:sc_run, 'complete', v:false) || reltimefloat(reltime()) >= s:sc_run.deadline
      let l:done = get(s:sc_run, 'complete', v:false)
      let l:last = len(getbufline(s:sc_bufnr, 1, '$'))
      call setbufline(s:sc_bufnr, l:last + 1, ['', 'status: ' . (l:done ? 'succeeded' : 'timed_out')])
      let s:sc_last_run = {
            \ 'scenario': s:sc_run.scenario,
            \ 'host_speed': s:sc_run.host_speed,
            \ 'kinds': s:sc_run.kinds,
            \ 'text': s:sc_run.text,
            \ 'complete': l:done,
            \ 'parse_errors': copy(s:sc_run.parse_errors),
            \ }
      let s:sc_run = {}
      if type(s:sc_timer) != type(v:null)
        call timer_stop(s:sc_timer)
        let s:sc_timer = v:null
      endif
    endif
    redraw
  finally
    let s:sc_pump_busy = 0
  endtry
endfunction

function! s:sc_send(op, payload) abort
  if !s:sc_start()
    throw 'stdio-contract host start failed'
  endif
  let l:req = {
        \ 'protocol_version': 1,
        \ 'request_id': printf('sc-%d', localtime()),
        \ 'op': a:op,
        \ 'payload': a:payload,
        \ }
  call s:sc_wirelog('SEND ' . json_encode(l:req))
  call ch_sendraw(s:sc_ch, json_encode(l:req) . "\n")
endfunction

function! ToasStdioContractRunAsyncFn(...) abort
  let l:scenario = get(a:, 1, 'baseline')
  let l:timeout_s = str2float(get(a:, 2, '10'))
  let l:host_speed = get(a:, 3, get(g:, 'toas_stdio_contract_speed', 'fast'))
  if !s:sc_start()
    throw 'stdio-contract host start failed'
  endif
  if type(s:sc_timer) != type(v:null)
    call timer_stop(s:sc_timer)
    let s:sc_timer = v:null
  endif
  let s:sc_rx = ''
  let s:sc_frames = []
  let s:sc_last_run = {}
  call s:sc_init_buffer(l:scenario, l:host_speed)
  let s:sc_run = {
        \ 'scenario': l:scenario,
        \ 'host_speed': l:host_speed,
        \ 'deadline': reltimefloat(reltime()) + l:timeout_s,
        \ 'text': '',
        \ 'kinds': [],
        \ 'complete': v:false,
        \ 'parse_errors': [],
        \ }
  call s:sc_send('stream_subscribe', {'run_id': 'sc-run', 'scenario': l:scenario, 'host_speed': l:host_speed})
  call s:sc_wirelog('RUN async scenario=' . l:scenario . ' speed=' . l:host_speed)
  let s:sc_timer = timer_start(16, function('s:sc_tick'), {'repeat': -1})
  return {'started': v:true, 'scenario': l:scenario, 'host_speed': l:host_speed}
endfunction

function! ToasStdioContractRunBlockingFn(...) abort
  let l:scenario = get(a:, 1, 'baseline')
  let l:timeout_s = str2float(get(a:, 2, '6'))
  let l:host_speed = get(a:, 3, get(g:, 'toas_stdio_contract_speed', 'fast'))
  call ToasStdioContractRunAsyncFn(l:scenario, l:timeout_s, l:host_speed)
  let l:deadline = reltimefloat(reltime()) + l:timeout_s
  while reltimefloat(reltime()) < l:deadline
    let l:last = ToasStdioContractLast()
    if type(l:last) == type({}) && !empty(l:last)
      return l:last
    endif
    sleep 20m
  endwhile
  return ToasStdioContractLast()
endfunction

function! ToasStdioContractLast() abort
  return s:sc_last_run
endfunction

command! -nargs=? ToasStdioContractStart call s:sc_start()
command! -nargs=0 ToasStdioContractStop call s:sc_stop()
command! -nargs=* ToasStdioContractRun call ToasStdioContractRunAsyncFn(<f-args>)
command! -nargs=* ToasStdioContractRunAsync call ToasStdioContractRunAsyncFn(<f-args>)
command! -nargs=* ToasStdioContractRunBlocking call ToasStdioContractRunBlockingFn(<f-args>)
