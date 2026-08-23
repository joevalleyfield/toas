" Vim syntax probe for TOAS transcripts.
" Deliberately defines semantic identities without linking them to colors.

if exists('b:toas_transcript_syntax_loaded')
  finish
endif
let b:toas_transcript_syntax_loaded = 1

syn case match

" A backslash-escaped less-than is Markdown prose, not an HTML/autolink start.
syn match toasEscapedLessThan '\\<'

" Headings carry the semantic identity. Turn regions below remain transparent
" so these matches can coexist with ordinary Markdown heading syntax.
syn match toasRoleSystem '^## TOAS:SYSTEM$'
syn match toasRoleUser '^## TOAS:USER$'
syn match toasRoleAssistant '^## TOAS:ASSISTANT$'
syn match toasRoleControl '^## TOAS:CONTROL$'
syn match toasResultHeading '^## RESULT$'
syn match toasSubregionAssistantHeading '^## ASSISTANT$'

" Language delegates are included by reference. The TOAS fence regions below
" decide when the delegated syntax is active.
syn include @toasYaml syntax/yaml.vim
unlet! b:current_syntax
syn include @toasToml syntax/toml.vim
unlet! b:current_syntax

syn region toasYamlFence
      \ matchgroup=toasFenceDelimiter
      \ start='^\s*```yaml\s*$'
      \ end='^\s*```\s*$\|^\ze## TOAS:\(SYSTEM\|USER\|ASSISTANT\|CONTROL\)$'
      \ keepend
      \ contains=@toasYaml

syn region toasTomlFence
      \ matchgroup=toasFenceDelimiter
      \ start='^\s*```toml\s*$'
      \ end='^\s*```\s*$\|^\ze## TOAS:\(SYSTEM\|USER\|ASSISTANT\|CONTROL\)$'
      \ keepend
      \ contains=@toasToml

syn region toasInertFence
      \ matchgroup=toasFenceDelimiter
      \ start='^\s*```inert\s*$'
      \ end='^\s*```\s*$\|^\ze## TOAS:\(SYSTEM\|USER\|ASSISTANT\|CONTROL\)$'
      \ keepend

" Role markers are explicit synchronization anchors. TOAS state never needs
" to be recovered from an earlier turn.
syn sync minlines=50
syn sync match toasRoleSync groupthere NONE '^## TOAS:\(SYSTEM\|USER\|ASSISTANT\|CONTROL\)$'

" First visual pass: use standard theme-owned groups. User-like roles share a
" treatment while retaining distinct syntax identities above.
hi def link toasRoleSystem Title
hi def link toasRoleUser Title
hi def link toasRoleControl Title
hi def link toasRoleAssistant Statement
hi def link toasResultHeading PreProc
hi def link toasSubregionAssistantHeading Special
hi def link toasFenceDelimiter Delimiter
hi def link toasInertFence Comment
