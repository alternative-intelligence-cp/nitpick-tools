" nitpick.vim - filetype detection for Nitpick (.npk)
" First written by Muse Wonder (Meta); checked, with one fix (the Type:name
" rule rewritten without a slow lookbehind), by Nitpick management
" (Claude Opus 5.5).
augroup nitpick_ftdetect
  autocmd!
  autocmd BufNewFile,BufRead *.npk setfiletype nitpick
augroup END
