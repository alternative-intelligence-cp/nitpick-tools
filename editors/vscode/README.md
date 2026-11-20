# Nitpick syntax highlighting (VS Code and other TextMate editors)

Colours Nitpick (`.npk`) source: keywords, the safety and contract words (`wild`, `raw`, `requires`, `ensures`, …), built-in types, every number form (`0FFhex`, `1011bin`, balanced ternary and nonary, type suffixes), the four string forms (plain, `"""block"""`, `r"raw"`, and `` `template &{…}` ``), comments and operators.

## Try it without installing
```
code --extensionDevelopmentPath=/path/to/nitpick-tools/editors/vscode some_file.npk
```
This opens a separate VS Code window with the highlighting loaded; your normal setup isn't changed.

## Install it
Package the folder as a VSIX with Microsoft's packaging tool, then install that file:
```
cd editors/vscode
npx @vscode/vsce package          # makes nitpick-0.1.0.vsix
code --install-extension nitpick-0.1.0.vsix
```
Other editors that read TextMate grammars (Sublime Text, and others) can use `nitpick.tmLanguage.json` directly.

## How it was checked (compiler commit `aefae6e`)
- All 170 keywords in the compiler's own keyword table are coloured, alone and mid-line; names that merely contain a keyword (`format`, `results`, `is_ok`) are not.
- All 1,562 `.npk` files in the compiler's repository highlight with no errors and nothing left open at the end of a file. A deliberately unterminated string and comment were used to confirm that check can fail.
- Tricky cases: `//` and `/*` inside strings, quotes in comments, escaped quotes, braces inside a template's `&{…}`, multi-line block strings, and number forms that aren't valid Nitpick (`0x…`, the retired C prefix, and `f128`, which has no literals) staying uncoloured.

The checks used VS Code's own TextMate engine (`vscode-textmate` 9.3.2).

## Not covered yet
- The name in a `Type:name` declaration isn't coloured separately; nor are struct fields, enum variants or trait methods.
- `#[…]` attributes have no region of their own.
- The grammar is a little more permissive than the compiler about which suffix suits which literal. The compiler is the judge; colours are a reading aid.

## Credits
First written by Muse Wonder (Meta) from the compiler's lexer and specification; checked, with one fix (`f128` removed as a literal suffix), by Nitpick management (Claude Opus 5.5).
