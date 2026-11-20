# Nitpick syntax highlighting for GNU nano

Colours Nitpick (`.npk`) source in nano: all of the compiler's keywords in groups (control, contracts, safety words such as `wild` and `raw`, async, declarations, modifiers, constants), built-in types, every number form (`0FFhex`, `1011bin`, balanced ternary `10Tt`, nonary, separators and type suffixes), strings, characters, escapes, comments and operators.

## Install it
```
mkdir -p ~/.nano
cp nitpick.nanorc ~/.nano/
echo 'include "~/.nano/nitpick.nanorc"' >> ~/.nanorc
```
nano then picks the colours up for any file ending in `.npk`. To try the file without changing your setup:
```
nano --rcfile=/path/to/a-file-that-includes-nitpick.nanorc some_file.npk
```
Tested on GNU nano 7.2. In nano 7.2 `--rcfile` replaces your usual settings for that run; `--ignorercfiles` would turn the colours off too.

## How it was checked (compiler commit `aefae6e`)
- All 170 keywords in the compiler's own keyword table are in the keyword rules: none missing, none extra.
- Colours were read off nano's screen (captured with `tmux capture-pane -e`). Words that merely contain a keyword (`forward`, `returns_x`, `whileish`) stay plain; the keyword alone is coloured.
- Every number form the file colours compiles with the compiler. Forms the compiler refuses stay uncoloured: `0xFF` (the retired C prefix), `102t` (`2` isn't a balanced-ternary digit), and `2.5f128` (`flt128` has no literals).
- Every `.npk` file in the compiler's repository was opened with it (about 1,560) with no errors or hangs; our re-check opened the 100 largest (up to 1 MB) in under 0.1 seconds each. A deliberately broken rule was used to confirm that a bad file is reported.

## What nano can't do
- **A `//` or `/*` inside a string is coloured as a comment.** nano has no "not inside a string" rule, so a `//` in a string greys out the rest of that line, and a `/*` greys out everything up to the next `*/`, across lines. The code is fine; only the colours are wrong.
- Block comments don't nest in Nitpick, and nano shows exactly that: `/* a /* b */ code` ends the comment at the first `*/`.
- Escapes are also coloured inside raw strings (`r"\n"`) and in template expressions (`&{…}`), and a `Type:name` declaration can't colour the name separately from the keyword.

## Credits
First written by Muse Wonder (Meta) from the compiler's lexer; checked, with two fixes (closing brackets weren't coloured; `NIL`, `NULL` and `ERR` were coloured as type names), by Nitpick management (Claude Opus 5.5).
