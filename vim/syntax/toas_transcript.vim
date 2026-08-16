" Vim syntax probe for TOAS transcripts.
" Deliberately defines semantic identities without linking them to colors.

if exists('b:toas_transcript_syntax_loaded')
  finish
endif
let b:toas_transcript_syntax_loaded = 1

syn case match

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
      \ end='^\s*```\s*$'
      \ keepend
      \ contains=@toasYaml

syn region toasTomlFence
      \ matchgroup=toasFenceDelimiter
      \ start='^\s*```toml\s*$'
      \ end='^\s*```\s*$'
      \ keepend
      \ contains=@toasToml

syn region toasInertFence
      \ matchgroup=toasFenceDelimiter
      \ start='^\s*```inert\s*$'
      \ end='^\s*```\s*$'
      \ keepend

" Role markers are explicit synchronization anchors. TOAS state never needs
" to be recovered from an earlier turn.
syn sync minlines=50
