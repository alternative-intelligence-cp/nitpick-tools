# Contributing to Nitpick Tools

Thank you for your interest in improving Nitpick's developer tooling!

## Repository Contents

- **nitpick-safety/** — Static safety audit tool (C)
- **nitpick-mcp/** — MCP server for AI-assisted Nitpick coding (Python)
- **vscode-nitpick/** — VS Code extension (TextMate grammar, JSON)
- **tree-sitter-nitpick/** — Tree-sitter grammar
- **emacs/** — Emacs major mode

## Getting Started

1. Fork the repository
2. Clone: `git clone https://github.com/<your-username>/nitpick-tools.git`
3. Create a branch: `git checkout -b feature/your-change`
4. Make your changes
5. Push and open a Pull Request

## VS Code Extension

The extension lives in `vscode-nitpick/`. To test changes:

1. Open `vscode-nitpick/` in VS Code
2. Press `F5` to launch the Extension Development Host
3. Open an `.npk` file to test syntax highlighting

The TextMate grammar is in `syntaxes/nitpick.tmLanguage.json`. Key scopes:
- Keywords: `func:`, `failsafe`, `pass()`, `fail()`, `till`, `use`
- Types: `int8`–`int128`, `flt32`/`flt64`, `str`, `bool`, `NIL`
- Preprocessor: `%define`, `%macro`, `%ifdef`, `%include`
- Compile-time: `comptime`, `inline`, `noinline`

## nitpick-safety (C)

```bash
cd nitpick-safety
make
./nitpick-safety ../path/to/file.npk
```

## nitpick-mcp (Python)

```bash
cd nitpick-mcp
pip install -r requirements.txt
python nitpick_mcp_server.py
```

## Commit Messages

Use conventional format:

```
type(scope): description

feat(vscode): add comptime keyword highlighting
fix(safety): handle nested borrow scopes
docs(mcp): update tool descriptions
```

## License

This project is licensed under AGPL-3.0. By contributing, you agree to license your contributions under the same terms.
