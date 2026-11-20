" nitpick.vim - syntax highlighting for Nitpick (.npk), for vim 8+/9.
" First written by Muse Wonder (Meta); checked, with one fix (the Type:name
" rule rewritten without a slow lookbehind), by Nitpick management
" (Claude Opus 5.5).
" Built from the lexer tables at nitpick commit aefae6e (src/frontend/
" keywords.npk, lexer.npk, numeric.npk, num_width.npk, escapes.npk,
" operators.npk); grouped as in the checked TextMate grammar and nanorc.

if exists("b:current_syntax")
  finish
endif

syntax case match

" --- escapes ---------------------------------------------------------------
" escapes.npk: \\ \n \r \t \" \' \0, \xHH and \u{...}. Marked contained:
" an escape colours only where a containing item asks for it -- inside
" plain and block strings and inside characters. Raw strings and template
" parts do not include it, so a backslash there stays string-coloured,
" which is what the lexer does (no escape processing in either).
syntax match npEscape "\\\(u{[0-9a-fA-F]\+}\|x[0-9a-fA-F]\{2\}\|.\)" contained

" --- strings, characters, templates ----------------------------------------
" skip=/\\./ so an escaped backslash before a quote (\"a\\") cannot make
" the closing quote look escaped. Plain strings are oneline (the lexer
" rejects a newline inside one); block strings may span lines.
syntax region npChar start="'" end="'" skip=/\\./ oneline contains=npEscape
syntax region npString start=/"/ skip=/\\./ end=/"/ oneline contains=npEscape
syntax region npString start=/"""/ end=/"""/ contains=npEscape
" Raw strings (lexer D-024): r"..." with no escape processing at all, so
" no contains -- a \n inside stays string-coloured.
syntax region npRawString start=/r"/ end=/"/ oneline
" Template strings: `...` with &{ ... } interpolation. The parts are
" string; the interpolation is ordinary code (contains=TOP). A region
" cannot count braces, so an interpolation whose expression contains a
" braced block ends at that block's first } -- see report.md.
syntax region npTemplate start="`" end="`" contains=npInterp
syntax region npInterp matchgroup=npInterpDelim start="&{" end="}" contained contains=TOP

" --- keywords --------------------------------------------------------------
" Every word of keywords.npk (170), grouped as in the TextMate grammar.
" The all-caps constants NIL, NULL and ERR are syn keywords here, and a
" keyword beats a match at the same position, so the capitalised-type
" match below can never repaint them as types (the nano file's bug).
" control (24)
syntax keyword npControl if else for while loop break continue return
syntax keyword npControl pass exit fail defer pick when fall then
syntax keyword npControl till end in is as on with where
" contract (9)
syntax keyword npContract requires ensures decreases invariant old result limit prove
syntax keyword npContract assert_static
" safety (13)
syntax keyword npSafety wild wildx raw move drop discard relay give
syntax keyword npSafety gives acquires joins never fails
" async (3)
syntax keyword npAsync async await thread
" memory-order (5)
syntax keyword npMemOrder acquire release acq_rel seq_cst relaxed
" builtin-fn (2)
syntax keyword npBuiltinFn is_err range
" declaration (11)
syntax keyword npDecl func struct enum trait impl mod use error
syntax keyword npDecl unit macro extern
" modifier (15)
syntax keyword npModifier pub fixed sealed hidden pure inline noinline nodrop
syntax keyword npModifier opaque assoc defaults comptime cfg derive unbounded
" language-constant (5)
syntax keyword npConstant true false NIL NULL ERR
" builtin-type (83)
syntax keyword npBuiltinType any dyn bool char8 char16 char32 int8 int16 nextgroup=npDeclColon
syntax keyword npBuiltinType int32 int64 int128 int256 int512 int1024 int2048 int4096 nextgroup=npDeclColon
syntax keyword npBuiltinType uint8 uint16 uint32 uint64 uint128 uint256 uint512 uint1024 nextgroup=npDeclColon
syntax keyword npBuiltinType uint2048 uint4096 flt32 flt64 flt128 flt256 flt512 frac8 nextgroup=npDeclColon
syntax keyword npBuiltinType frac16 frac32 frac64 tfp32 tfp64 tfp128 tfp256 tbb8 nextgroup=npDeclColon
syntax keyword npBuiltinType tbb16 tbb32 tbb64 tbb128 tbb256 dim256 nit trit nextgroup=npDeclColon
syntax keyword npBuiltinType tryte nyte string cstring buffer atomic array simd nextgroup=npDeclColon
syntax keyword npBuiltinType complex arena shared_arena stack Result Optional Future Handle nextgroup=npDeclColon
syntax keyword npBuiltinType Guard Mutex RGuard RwLock Barrier Channel CondVar OwnedFd nextgroup=npDeclColon
syntax keyword npBuiltinType Self Rules pid tid uid gid fd prot nextgroup=npDeclColon
syntax keyword npBuiltinType oflags mflags fmode nextgroup=npDeclColon

" Capitalised names that are not keywords: user and prelude types
" (Meters, Seconds, MyStruct, ...).
syntax match npTypeName "\<[A-Z][A-Za-z0-9_]*\>" nextgroup=npDeclColon

" A Type:name declaration colours the declared name separately. A type word
" (built-in or capitalised) offers a following colon (nextgroup), and that
" colon offers a name. No lookbehind: an earlier draft used one, and it cost
" about 4 ms a line (9 s to parse 2,000 lines of a large test file, against
" 0.3 s without it). Only Type:name is done; mod:name and func:name are not.
syntax match npDeclColon ":" contained nextgroup=npDeclName
syntax match npDeclName "\<[A-Za-z_][A-Za-z0-9_]*\>" contained

" --- numbers ---------------------------------------------------------------
" numeric.npk / num_width.npk. Bases are spelled as suffixes -- hex, bin,
" oct, ter/tri/t, non/n -- never 0x/0b prefixes. A float must contain a
" dot (FloatLiteral ::= DecimalLiteral "." DecimalLiteral Exponent?
" TypeSuffix?), so 1e3 is not a float. flt128 is storage-only (D-143)
" and has no literals: there is deliberately no f128 suffix anywhere.
syntax match npNumber "\<[0-9][0-9_]*\>"
syntax match npNumber "\<[0-9][0-9_]*\(\(i\|u\)\(8\|16\|32\|64\|128\|256\|512\|1024\|2048\|4096\)\|tbb\(8\|16\|32\|64\|128\|256\)\)\>"
syntax match npNumber "\<[0-9][0-9_]*\(char8\|char16\|char32\)\>"
syntax match npNumber "\<[0-9][0-9A-Fa-f_]*hex\(\(i\|u\)\(8\|16\|32\|64\|128\|256\|512\|1024\|2048\|4096\)\|tbb\(8\|16\|32\|64\|128\|256\)\)\?\>"
syntax match npNumber "\<[01][01_]*bin\(\(i\|u\)\(8\|16\|32\|64\|128\|256\|512\|1024\|2048\|4096\)\|tbb\(8\|16\|32\|64\|128\|256\)\)\?\>"
syntax match npNumber "\<[0-7][0-7_]*oct\(\(i\|u\)\(8\|16\|32\|64\|128\|256\|512\|1024\|2048\|4096\)\|tbb\(8\|16\|32\|64\|128\|256\)\)\?\>"
syntax match npNumber "\<[01][01Tt_]*ter\(\(i\|u\)\(8\|16\|32\|64\|128\|256\|512\|1024\|2048\|4096\)\|tbb\(8\|16\|32\|64\|128\|256\)\)\?\>"
syntax match npNumber "\<[01][01Tt_]*tri\(\(i\|u\)\(8\|16\|32\|64\|128\|256\|512\|1024\|2048\|4096\)\|tbb\(8\|16\|32\|64\|128\|256\)\)\?\>"
syntax match npNumber "\<[01][01Tt_]*t\(\(i\|u\)\(8\|16\|32\|64\|128\|256\|512\|1024\|2048\|4096\)\|tbb\(8\|16\|32\|64\|128\|256\)\)\?\>"
syntax match npNumber "\<[0-4][0-4A-Da-d_]*non\(\(i\|u\)\(8\|16\|32\|64\|128\|256\|512\|1024\|2048\|4096\)\|tbb\(8\|16\|32\|64\|128\|256\)\)\?\>"
syntax match npNumber "\<[0-4][0-4A-Da-d_]*n\(\(i\|u\)\(8\|16\|32\|64\|128\|256\|512\|1024\|2048\|4096\)\|tbb\(8\|16\|32\|64\|128\|256\)\)\?\>"
syntax match npNumber "\<[0-9][0-9_]*\(f32\|f64\|tfp32\|tfp64\|tfp128\|tfp256\|dim256\)\>"
syntax match npNumber "\<[0-9][0-9_]*\.[0-9][0-9_]*\([eE][+-]\?[0-9][0-9_]*\)\?\(f32\|f64\|tfp32\|tfp64\|tfp128\|tfp256\|dim256\)\?\>"

" --- operators -------------------------------------------------------------
" operators.npk. Single characters and punctuation first; the multi-
" character spellings are defined after them so they win at the same
" position (:: < over :, =>! over =, .. over .). Brackets are operators,
" opening AND closing (the nano file missed the closing ones).
syntax match npOperator "[$@+*/%=<>!&|^~#?-]"
syntax match npOperator "[:;,]"
syntax match npOperator "\."
syntax match npOperator "[\[\](){}]"
syntax match npOperator "=>!"
syntax match npOperator "??!"
syntax match npOperator "?!"
syntax match npOperator "?|"
syntax match npOperator "?\."
syntax match npOperator "??"
syntax match npOperator "\.\.\*"
syntax match npOperator "\.\.\."
syntax match npOperator "\.\.\^"
syntax match npOperator "\.\."
syntax match npOperator "<=>"
syntax match npOperator "=>"
syntax match npOperator "<-"
syntax match npOperator "->"
syntax match npOperator "<<=\|>>=\|<<\|>>"
syntax match npOperator "<=\|>=\|==\|!="
syntax match npOperator "+%\|+%=\|\*%\|\*%="
syntax match npOperator "-%\|-%="
syntax match npOperator "&&"
syntax match npOperator "||"
syntax match npOperator "++\|--"
syntax match npOperator "+=\|-=\|\*=\|%=\|/=\|&=\|\^="
syntax match npOperator "|="
syntax match npOperator "!!!"
syntax match npOperator "<|"
syntax match npOperator "|>"
syntax match npOperator "\$\$[im]"
syntax match npOperator "_[?!~^]"
syntax match npOperator "::<"

" --- comments --------------------------------------------------------------
" Defined last on purpose: at the same start position the item defined
" later wins, and a comment must beat the single-character operator
" match for / (an earlier draft defined comments first and every comment
" lost to the operator class). This is safe next to strings: a string
" region starts at its quote, before any // inside it, and inside the
" region only its contained items can match, so the comment never starts
" there; inside a comment, no string can start either.
" The lexer ends a block comment at the first */ -- Nitpick block
" comments do not nest -- and a vim region does exactly the same.
syntax match npComment "//.*$"
syntax region npComment start="/\*" end="\*/"

" --- highlight links ---------------------------------------------------------
highlight default link npControl Keyword
highlight default link npContract PreProc
highlight default link npSafety Keyword
highlight default link npAsync Keyword
highlight default link npMemOrder Constant
highlight default link npBuiltinFn Function
highlight default link npDecl StorageClass
highlight default link npModifier StorageClass
highlight default link npConstant Constant
highlight default link npBuiltinType Type
highlight default link npTypeName Type
highlight default link npDeclName Identifier
highlight default link npDeclColon Operator
highlight default link npComment Comment
highlight default link npString String
highlight default link npRawString String
highlight default link npTemplate String
highlight default link npInterpDelim Delimiter
highlight default link npChar Character
highlight default link npEscape SpecialChar
highlight default link npNumber Number
highlight default link npOperator Operator

let b:current_syntax = "nitpick"
