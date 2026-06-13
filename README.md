# nitpick-tools

<p align="center">
	<img src="assets/nitpick_logo.png" alt="Nitpick logo: raccoon holding a magnifying glass" width="220">
</p>

[![CI](https://github.com/alternative-intelligence-cp/nitpick-tools/actions/workflows/ci.yml/badge.svg)](https://github.com/alternative-intelligence-cp/nitpick-tools/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)

> 🚧 **Rebrand in progress:** Aria is becoming **Nitpick**. This tooling repo
> still uses Aria names while the migration is underway. Editor grammars,
> generated extension assets, and tool command names need compatibility planning
> before any breaking rename.

Developer tools for the [Nitpick programming language](https://github.com/alternative-intelligence-cp/nitpick).

## Components

### nitpick-ls (Language Server)
LSP-compatible language server bundled with the main compiler. Provides diagnostics, hover, go-to-definition, completion, document symbols, references, and signature help. Source lives in the [nitpick repo](https://github.com/alternative-intelligence-cp/nitpick) at `src/tools/lsp/`.

### nitpick-safety (Static Auditor)
Static safety audit tool for Nitpick source files. Written in C. Scans for `wild`/`raw`/`drop`/`ok` usages, relaxed atomics, FFI boundaries, unsafe blocks, and trivial failsafe handlers.

```bash
cd nitpick-safety && make
./nitpick-safety path/to/file.npk
./nitpick-safety --json path/to/project/   # JSON output
./nitpick-safety --summary path/to/project/# per-tag statistics
```

### nitpick-mcp (MCP Server)
[Model Context Protocol](https://modelcontextprotocol.io/) server for AI-assisted Nitpick development. Zero external dependencies — pure Python 3.8+ stdlib. Provides 5 tools: `nitpick_compile`, `nitpick_check`, `nitpick_docs`, `nitpick_format`, `nitpick_ask`.

```bash
python3 nitpick-mcp/nitpick_mcp.py
```

### VS Code Extension
Full VS Code extension with TextMate syntax highlighting, LSP integration (nitpick-ls), DAP debug adapter integration, and language configuration. Located in `editors/vscode/`.

### Editor Support
- **tree-sitter-nitpick** — Tree-sitter grammar for Neovim, Helix, and other tree-sitter editors
- **emacs** — Emacs major mode (`nitpick-mode.el`) with full syntax highlighting, indentation, and typed literal support
- **vscode-nitpick** — Legacy VS Code syntax extension (superseded by `editors/vscode/`)

## License

AGPL-3.0 — see [LICENSE.md](LICENSE.md)
