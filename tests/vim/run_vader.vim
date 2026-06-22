set nocompatible
let s:root = fnamemodify(getcwd(), ':p')
execute 'set rtp^=' . fnameescape(s:root . 'tests/vendor/vader.vim')
execute 'set rtp^=' . fnameescape(s:root)
runtime! plugin/vader.vim
runtime! vim/plugin/toas.vim
execute 'Vader!' 'tests/vim/*.vader'
