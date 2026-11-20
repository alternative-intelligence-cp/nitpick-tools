" nitpick.vim - filetype plugin for Nitpick (.npk)
" First written by Muse Wonder (Meta); checked, with one fix (the Type:name
" rule rewritten without a slow lookbehind), by Nitpick management
" (Claude Opus 5.5).
if exists("b:did_ftplugin")
  finish
endif
let b:did_ftplugin = 1

setlocal commentstring=//\ %s
setlocal comments=s1:/*,mb:*,ex:*/,://

let b:undo_ftplugin = "setlocal commentstring< comments<"
