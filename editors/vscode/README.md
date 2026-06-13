# Nitpick Language Support for VS Code

Rich language support for the [Nitpick programming language](https://github.com/nitpick-lang/nitpick) in Visual Studio Code.

## Features

### 🎨 Syntax Highlighting
- Full TextMate grammar with semantic coloring
- TBB types (tbb8, tbb16, tbb32, tbb64)
- Balanced ternary types (trit, tryte, nit, nyte)
- Memory qualifiers (@wild, @gc, @stack, @wildx)
- String interpolation (`&{expression}`)
- Keywords, operators, and control flow

### 🔍 Language Server Features
- **Real-time Diagnostics**: Syntax and semantic errors as you type
- **Hover Information**: Type information and documentation
- **Go to Definition**: Navigate to symbol declarations
- **Auto-completion** *(coming soon)*
- **Code Formatting** *(coming soon)*

### ⚙️ Smart Editing
- Auto-closing pairs: `{}`, `[]`, `()`, `""`, `''`, ` `` `
- Special: `&{` auto-closes with `}` for string interpolation
- Block comments: `/* */`
- Line comments: `//`
- Bracket matching and folding

## Requirements

The extension bundles the Nitpick language server (`nitpick-ls`) for all platforms:
- Linux (x86_64)
- macOS (Universal)
- Windows (x86_64)

Alternatively, you can:
1. Install the Nitpick compiler from [releases](https://github.com/nitpick-lang/nitpick/releases)
2. Build from source: `cd nitpick && cmake --build build`

## Extension Settings

This extension contributes the following settings:

* `nitpick.server.path`: Path to `nitpick-ls` executable (uses bundled binary if empty)
* `nitpick.server.args`: Additional arguments to pass to the language server
* `nitpick.trace.server`: Traces LSP communication (`off`, `messages`, `verbose`)

## Usage

1. Install the extension
2. Open any `.npk` file
3. The language server starts automatically
4. Enjoy instant feedback!

### Example Nitpick Code

```nitpick
// Nitpick with TBB types and memory safety
func:fibonacci = (n: tbb32) -> tbb32 {
    if (n <= 1) {
        return n;
    }
    return fibonacci(n - 1) + fibonacci(n - 2);
}

// Hybrid memory model
var obj:MyStruct = @gc { x: 10, y: 20 };
wild int32*:ptr = #obj.x;  // Pin and get pointer
defer {
    // Cleanup
}
```

## Known Issues

- Semantic tokens not yet implemented (Phase 7.3.6+)
- Code completion under development
- Format-on-save coming soon

## Release Notes

### 0.2.0 (March 2026)

- Updated to match Nitpick compiler v0.2.0

### 0.1.0 (December 2025)

Initial release:
- TextMate grammar for syntax highlighting
- LSP integration with nitpick-ls
- Real-time diagnostics
- Hover and go-to-definition
- Cross-platform bundled binaries

## Building from Source

```bash
cd editors/vscode
npm install
npm run compile
```

### Packaging

```bash
npm run package
# Produces: nitpick-lang-0.2.0.vsix
```

### Installing Locally

```bash
code --install-extension nitpick-lang-0.2.0.vsix
```

## Contributing

Contributions welcome! See [CONTRIBUTING.md](../../CONTRIBUTING.md)

## License

MIT License - see [LICENSE](../../LICENSE)

---

**Enjoy coding in Nitpick!** 🚀
