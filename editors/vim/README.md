# Nitpick syntax highlighting for vim

Colours Nitpick (`.npk`) source in vim 8 and 9: all of the compiler's keywords in groups (control, contracts, safety words such as `wild` and `raw`, async, declarations, modifiers, constants), built-in and capitalised type names, the declared name in `Type:name`, every number form (`0FFhex`, `1011bin`, balanced ternary `10Tt`, nonary, separators and type suffixes), plain, block, raw and template strings, characters, escapes, comments and operators. It also sets `commentstring` so comment commands use `//`.

Unlike the nano file, it knows what's inside a string: a `//` or `/*` in a string stays string, and escapes such as `\n` are coloured only in strings that process them (not in `r"raw"` strings).

## Install it
As a vim package (vim 8 or later):
```
mkdir -p ~/.vim/pack/nitpick/start
cp -r editors/vim ~/.vim/pack/nitpick/start/nitpick
```
Any file ending in `.npk` is then highlighted. You need `syntax on` and `filetype plugin on` in your `~/.vimrc` (most setups have them). For Neovim, copy it to `~/.local/share/nvim/site/pack/nitpick/start/nitpick` instead (not tested there yet).

## How it was checked (compiler commit `aefae6e`, vim 9.1)
- All 170 keywords in the compiler's own keyword table are in the keyword lists: none missing, none extra.
- Each token's highlight group was read from vim itself, headless (`synIDattr(synIDtrans(synID(…)))`). There were 198 probes in one test file, plus a separate file of hard cases, all as expected. Controls: words that merely contain a keyword (`forward`, `returns_x`, `is_errx`) stay plain; `//` and `/*` inside strings stay string; `/* a /* b */ code` ends at the first `*/` (block comments don't nest in Nitpick); closing brackets and `NIL`/`NULL`/`ERR` get their own colours.
- Forms the compiler refuses stay uncoloured: `0xFF` (the retired C prefix), `102t` (`2` isn't a balanced-ternary digit), and `2.5f128` (`flt128` has no literals).
- Every `.npk` file in the compiler's repository (1,562) was parsed from top to bottom with no errors, none taking over 2 seconds.

## Limits
- An interpolation whose expression contains its own braces (`&{ if (x) { … } }`) ends at the first `}`; vim regions can't count braces. Simple ones (`&{a + b}`) are exact.
- Only `Type:name` declarations colour the name. `mod:name`, `func:name` and array declarations such as `int32[4]:arr` don't.
- Function-call names aren't coloured.

## Credits
First written by Muse Wonder (Meta) from the compiler's lexer. Checked by Nitpick management (Claude Opus 5.5), with one fix: the `Type:name` rule used a lookbehind that slowed vim to about 4 ms per line on large files, and it was rewritten as a `nextgroup` chain, with the same colours about 34 times faster.
