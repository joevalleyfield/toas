if exists('g:loaded_toas_plugin')
  finish
endif
let g:loaded_toas_plugin = 1

let s:toas_channel = v:null

function! s:toas_socket_path() abort
  if exists('g:toas_socket_path')
    return g:toas_socket_path
  endif
  return getcwd() . '/.toas.sock'
endfunction

function! s:toas_request_id() abort
  return printf('%d-%d', localtime(), reltimefloat(reltime()) * 1000000)
endfunction

function! s:toas_channel_open() abort
  if !exists('*ch_open') || !exists('*ch_status') || !exists('*ch_evalexpr')
    return 0
  endif

  if type(s:toas_channel) == type(0) && ch_status(s:toas_channel) ==# 'open'
    return 1
  endif

  let l:addr = 'unix:' . s:toas_socket_path()
  let s:toas_channel = ch_open(l:addr, {'mode': 'json', 'waittime': 5000})
  return type(s:toas_channel) == type(0) && ch_status(s:toas_channel) ==# 'open'
endfunction

function! s:toas_step_rpc() abort
  if !s:toas_channel_open()
    return ''
  endif

  let l:req = {
        \ 'protocol_version': 1,
        \ 'request_id': s:toas_request_id(),
        \ 'op': 'step',
        \ 'payload': {},
        \ }

  let l:resp = ch_evalexpr(s:toas_channel, l:req, {'timeout': 5000})
  if type(l:resp) != type({})
    throw 'invalid rpc response'
  endif
  if get(l:resp, 'ok', v:false)
    return get(get(l:resp, 'payload', {}), 'stdout', '')
  endif

  let l:err = get(l:resp, 'error', {})
  throw printf('rpc error: %s', get(l:err, 'message', 'unknown'))
endfunction

function! s:insert_text_after_cursor(text) abort
  if a:text ==# ''
    return
  endif
  let l:lines = split(a:text, "\n", 1)
  if !empty(l:lines) && l:lines[-1] ==# ''
    call remove(l:lines, -1)
  endif
  if empty(l:lines)
    return
  endif
  call append(line('.'), l:lines)
endfunction

function! ToasStep() abort
  try
    let l:out = s:toas_step_rpc()
    call s:insert_text_after_cursor(l:out)
    return
  catch
  endtry

  execute 'silent read !toas step'
endfunction

command! ToasStep call ToasStep()
