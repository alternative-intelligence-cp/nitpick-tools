# nitpick-tools

Tools for working with [Nitpick](https://github.com/alternative-intelligence-cp/nitpick), a systems programming language for safety-critical software. Guides and examples are in [nitpick-docs](https://github.com/alternative-intelligence-cp/nitpick-docs).

These are early versions: small, tested, and honest about what they don't cover yet.

## What's here

| Folder | What | Status |
|---|---|---|
| [`editors/vscode/`](editors/vscode/) | Syntax highlighting for `.npk` files: a TextMate grammar, which VS Code, Sublime Text and many other editors can use | v0.1, checked against the compiler at `aefae6e` |
| [`editors/nano/`](editors/nano/) | Syntax highlighting for `.npk` files in GNU nano | v0.1, checked against the compiler at `aefae6e` |
| [`editors/vim/`](editors/vim/) | Syntax highlighting for `.npk` files in vim | v0.1, checked against the compiler at `aefae6e` |
| [`editors/emacs/`](editors/emacs/) | `nitpick-mode`, highlighting for `.npk` files in Emacs | v0.1, checked against the compiler at `aefae6e` |

## Planned

- **An audit helper:** lists every place in a program that a safety reviewer must look at (`wild` memory, `raw` calls, relaxed atomics and the like) with file and line, as a checklist, so nothing is missed. It will use the compiler's own front end rather than text matching, so it can't be fooled by comments, strings or macros.

## Credits

The tools here are written mostly by AI models. Each folder's README says which model did what, and how it was checked.

## Licence

Apache License 2.0; see [LICENSE](LICENSE).
