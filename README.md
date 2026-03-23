# aria-tools

Developer tools for the [Aria programming language](https://github.com/alternative-intelligence-cp/aria).

## Components

### aria-safety
Static safety audit tool for Aria source files. Written in C.

```bash
cd aria-safety && make
./aria-safety path/to/file.aria
./aria-safety --json path/to/project/   # JSON output
```

### aria-mcp
[Model Context Protocol](https://modelcontextprotocol.io/) server for AI-assisted Aria development. Written in Python.

```bash
pip install mcp
python aria-mcp/aria_mcp.py
```

### editors
Editor support for Aria:
- **tree-sitter-aria** — Tree-sitter grammar for syntax highlighting
- **emacs** — Emacs major mode (`aria-mode.el`)
- **vscode** — Legacy VS Code syntax (see vscode-aria for full extension)

### vscode-aria
Full VS Code extension with syntax highlighting, snippets, and language configuration.

```bash
cd vscode-aria
# Install via VS Code: Extensions → Install from VSIX
```

## License

AGPL-3.0 — see [LICENSE.md](LICENSE.md)
