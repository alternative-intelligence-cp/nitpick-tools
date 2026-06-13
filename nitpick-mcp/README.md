# nitpick-mcp

MCP (Model Context Protocol) server for the Nitpick language toolchain.
Exposes `nitpick_compile`, `nitpick_check`, `nitpick_docs`, `nitpick_format`, and
`nitpick_ask` as MCP tools so any MCP-capable AI assistant can compile,
audit, format, and answer questions about Nitpick code directly within a
conversation. Also exposes `nitpick_ref.md` sections as MCP resources.

**Zero external dependencies** — pure Python 3.8+ stdlib.

## Tools

| Tool | What it does |
|------|-------------|
| `nitpick_compile(source)` | Compile Nitpick source via `nitpickc`; returns `{ success, errors[], warnings[], output }` |
| `nitpick_check(source)` | Run `nitpick-safety` audit; returns `{ issues: [{ line, tag, message }] }` |
| `nitpick_docs(query)` | Section-level search over `nitpick_ref.md`; returns matching excerpts |
| `nitpick_format(source)` | Basic indentation/whitespace normalizer |
| `nitpick_ask(question[, context])` | Query the Nitpick specialist fine-tuned model (optional; set `ARIA_ASK_DISABLED=1` to hide) |

### nitpick_compile

```json
{ "source": "func:main = void() { stdout.write(`hello`); }" }
```
```json
{ "success": true, "errors": [], "warnings": [], "output": "" }
```

### nitpick_check

```json
{ "source": "wild int32*:p = nitpick.alloc(64);" }
```
```json
{
  "issues": [
    { "line": 1, "tag": "WILD", "message": "wild allocation — no GC safety; manual lifetime required" }
  ]
}
```

### nitpick_docs

```json
{ "query": "result propagation" }
```
Returns the relevant section(s) from `nitpick_ref.md`.

## Configuration

### VS Code / GitHub Copilot (`.vscode/mcp.json`)

```json
{
  "servers": {
    "nitpick": {
      "type": "stdio",
      "command": "python3",
      "args": ["/path/to/nitpick/tools/nitpick-mcp/nitpick_mcp.py"]
    }
  }
}
```

### Claude Desktop (`claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "nitpick": {
      "command": "python3",
      "args": ["/path/to/nitpick/tools/nitpick-mcp/nitpick_mcp.py"]
    }
  }
}
```

### Cursor (`.cursor/mcp.json`)

```json
{
  "mcpServers": {
    "nitpick": {
      "command": "python3",
      "args": ["/path/to/nitpick/tools/nitpick-mcp/nitpick_mcp.py"]
    }
  }
}
```

## Binary Discovery

The server finds `nitpickc` and `nitpick-safety` automatically:

1. **Environment variable** — `ARIAC_BIN` / `ARIA_SAFETY_BIN`
2. **Repo-relative paths** — `<repo>/build/nitpickc` and
   `<repo>/tools/nitpick-safety/nitpick-safety`
3. **`$PATH`**

Override if needed:

```sh
ARIAC_BIN=/custom/path/nitpickc python3 nitpick_mcp.py
```

Override the reference doc path:

```sh
ARIA_REF_MD=/custom/nitpick_ref.md python3 nitpick_mcp.py
```

## Running Manually

Start the server (reads JSON-RPC on stdin, writes on stdout):

```sh
python3 nitpick_mcp.py
```

Quick smoke-test:

```sh
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","clientInfo":{"name":"test","version":"0"},"capabilities":{}}}' \
  | python3 nitpick_mcp.py
```

List tools:

```sh
printf '%s\n%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","clientInfo":{"name":"test","version":"0"},"capabilities":{}}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
  | python3 nitpick_mcp.py
```

## Transport

stdio, JSON-RPC 2.0, newline-delimited (one JSON object per line).
Compatible with any MCP client that supports the `2024-11-05` protocol version.
