# Nitpick highlighting for Emacs

`nitpick-mode`, a small major mode for Nitpick (`.npk`) files. It colours all of the compiler's keywords in groups (control, contracts, safety words such as `wild` and `raw`, async, declarations, modifiers, constants), built-in and capitalised type names, the declared name in `Type:name`, every number form (`0FFhex`, `1011bin`, balanced ternary `10Tt`, nonary, separators and type suffixes), strings, characters, escapes, comments, operators and brackets. Comment commands (`M-;`) use `//`.

Strings and comments are read by Emacs's own parser, so a `//` or `/*` inside a string stays string, and escapes such as `\n` are coloured only in strings that process them (not in `r"raw"` strings).

## Install it
```
mkdir -p ~/.emacs.d/lisp
cp nitpick-mode.el ~/.emacs.d/lisp/
```
Then add to `~/.emacs.d/init.el` (or `~/.emacs`):
```elisp
(add-to-list 'load-path "~/.emacs.d/lisp")
(require 'nitpick-mode)
```
Any file ending in `.npk` then opens in `nitpick-mode`. Written for **Emacs 29 or later**. On older versions, operators, brackets and escapes have no face of their own and stay uncoloured; everything else works.

## How it was checked (compiler commit `aefae6e`, GNU Emacs 29.3)
- All 170 keywords in the compiler's own keyword table are in the mode's lists: none missing, none extra.
- Each token's face was read from Emacs itself, headless (`font-lock-ensure`, then `get-text-property … 'face`). There were 272 probes in one test file and a separate file of hard cases, all as expected. Controls: words that merely contain a keyword (`forward`, `returns_x`, `is_errx`) stay plain; `//` and `/*` inside strings stay string; `/* a /* b */ code` ends at the first `*/` (block comments don't nest in Nitpick); `"a\\"` and `'\''` end where they should; `NIL`/`NULL`/`ERR` are constants, not types.
- Forms the compiler refuses stay uncoloured: `0xFF` (the retired C prefix), `102t` (`2` isn't a balanced-ternary digit), and `2.5f128` (`flt128` has no literals).
- Every `.npk` file in the compiler's repository (1,562) was coloured from top to bottom with no errors, in 25 seconds in all; the slowest file (about 1 MB) took 0.7 s.
- It byte-compiles with no warnings, and the install steps above were tried with a fresh home folder.

## Limits
- Template strings (`` `…&{expr}…` ``) are coloured as strings whole; the `&{…}` expression isn't coloured separately.
- Characters use the string face (their escapes are coloured).
- The `r` of a raw string isn't coloured with the string.
- Only `Type:name` declarations colour the name; `mod:name`, `func:name` and array declarations such as `int32[4]:arr` don't. Function-call names aren't coloured.

## Credits
First written by Muse Wonder (Meta) from the compiler's lexer; checked by Nitpick management (Claude Opus 5.5), with no changes needed.
