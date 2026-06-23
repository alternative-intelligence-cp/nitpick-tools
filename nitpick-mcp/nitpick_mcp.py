#!/usr/bin/env python3
"""
nitpick-mcp — MCP stdio server for the Nitpick language toolchain.

Transport : stdio (JSON-RPC 2.0, newline-delimited)
Zero deps : pure Python 3.8+ stdlib only

Tools:
  nitpick_compile(source)            — compile Nitpick source via nitpickc, structured result
  nitpick_check(source)              — run nitpick-safety audit, structured findings
  nitpick_docs(query)                — section-level search over nitpick_ref.md
  nitpick_format(source)             — basic indentation/whitespace normalizer
  nitpick_ask(question[, context])   — query the Nitpick specialist fine-tuned model
"""

import json
import sys
import os
import subprocess
import tempfile
import re
import shutil
import threading
import time
from pathlib import Path

# ── dynamic root resolution ────────────────────────────────────────────────

def find_workspace_root(start_path: Path) -> Path:
    current = start_path
    while current.parent != current:
        if (current / "build.abc").exists() or (current / "nitpick.toml").exists() or (current / ".git").exists():
            return current
        current = current.parent
    return start_path

def find_nitpick_repo_root(start_path: Path) -> Path:
    # Try to find the nitpick repository root containing nitpick compiler
    current = start_path
    while current.parent != current:
        if (current / "nitpick").is_dir() and (current / "nitpick" / "build" / "npkc").exists():
            return current / "nitpick"
        if (current / "build" / "npkc").exists() and (current / "src" / "compiler").exists():
            return current
        current = current.parent
    
    # Fallback to standard locations
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent.parent
    if (repo_root / "nitpick").exists():
        return repo_root / "nitpick"
    if (repo_root / "aria").exists():
        return repo_root / "aria"
    return repo_root / "nitpick"

WORKSPACE_ROOT = find_workspace_root(Path(os.getcwd()).resolve())
NITPICK_ROOT = find_nitpick_repo_root(WORKSPACE_ROOT)

def _find_bin(env_var: str, *candidates: Path) -> str | None:
    v = os.environ.get(env_var)
    if v and Path(v).is_file() and os.access(v, os.X_OK):
        return v
    for c in candidates:
        if c.is_file() and os.access(c, os.X_OK):
            return str(c)
    return None

NITPICKC_BIN = _find_bin("NITPICKC_BIN",
                         NITPICK_ROOT / "build" / "npkc",
                         NITPICK_ROOT / "build" / "nitpickc",
                         WORKSPACE_ROOT / "build" / "npkc") or shutil.which("npkc") or shutil.which("nitpickc")

SAFETY_BIN = _find_bin("NITPICK_SAFETY_BIN",
                         WORKSPACE_ROOT / "nitpick-tools" / "nitpick-safety" / "nitpick-safety",
                         WORKSPACE_ROOT / "tools" / "nitpick-safety" / "nitpick-safety",
                         NITPICK_ROOT.parent / "nitpick-tools" / "nitpick-safety" / "nitpick-safety") or shutil.which("nitpick-safety")

def _find_ref_md() -> str:
    env = os.environ.get("NITPICK_REF_MD")
    if env and Path(env).is_file():
        return env
    candidates = [
        WORKSPACE_ROOT / "nitpick-docs" / "reference" / "nitpick_ref.md",
        NITPICK_ROOT.parent / "nitpick-docs" / "reference" / "nitpick_ref.md",
        NITPICK_ROOT / "docs" / "nitpick_ref.md",
        Path(__file__).resolve().parent.parent.parent / "nitpick-docs" / "reference" / "nitpick_ref.md"
    ]
    for c in candidates:
        if c.is_file():
            return str(c)
    return str(candidates[0])

NITPICK_REF_MD = _find_ref_md()
SPECIALIST_SCRIPT = os.environ.get("SPECIALIST_SCRIPT") or str(WORKSPACE_ROOT / "aria-specialist" / "nitpick_specialist_server.py")
NITPICK_ASK_DISABLED = os.environ.get("NITPICK_ASK_DISABLED", "").strip() not in ("", "0")

# ── nitpick_ask: specialist model proxy ────────────────────────────────────────

READY_TIMEOUT = 240

class _SpecialistProxy:
    def __init__(self) -> None:
        self._proc: subprocess.Popen | None = None
        self._lock  = threading.Lock()
        self._req_id = 0
        self._ready  = False

    def _start(self) -> str | None:
        if not os.path.isfile(SPECIALIST_SCRIPT):
            return f"specialist server not found: {SPECIALIST_SCRIPT}"
        try:
            self._proc = subprocess.Popen(
                [sys.executable, SPECIALIST_SCRIPT],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, bufsize=1,
            )
        except OSError as exc:
            return f"failed to start specialist server: {exc}"

        deadline = time.monotonic() + READY_TIMEOUT
        while time.monotonic() < deadline:
            if self._proc.poll() is not None:
                return "specialist server exited during startup"
            try:
                line = self._proc.stdout.readline()
            except OSError:
                return "specialist server stdout closed during startup"
            if not line:
                time.sleep(0.1)
                continue
            try:
                msg = json.loads(line)
                if msg.get("ready"):
                    self._ready = True
                    return None
            except json.JSONDecodeError:
                pass
        self._proc.kill()
        return f"specialist server did not become ready within {READY_TIMEOUT} s"

    def ask(self, question: str, context: str = "", max_tokens: int = 512, temperature: float = 0.2) -> dict:
        with self._lock:
            if self._proc is None or self._proc.poll() is not None:
                self._ready = False
                err = self._start()
                if err: return {"ok": False, "error": err}
            self._req_id += 1
            req = json.dumps({"id": self._req_id, "instruction": question, "context": context, "max_tokens": max_tokens, "temperature": temperature})
            try:
                self._proc.stdin.write(req + "\n")
                self._proc.stdin.flush()
                line = self._proc.stdout.readline()
            except OSError as exc:
                self._proc = None
                return {"ok": False, "error": f"specialist server I/O error: {exc}"}
            if not line:
                self._proc = None
                return {"ok": False, "error": "specialist server closed connection"}
            try:
                return json.loads(line)
            except json.JSONDecodeError as exc:
                return {"ok": False, "error": f"malformed response from specialist: {exc}"}

_SPECIALIST = _SpecialistProxy()

def nitpick_ask(question: str, context: str = "", max_tokens: int = 512, temperature: float = 0.2) -> dict:
    resp = _SPECIALIST.ask(question, context, max_tokens, temperature)
    if not resp.get("ok"):
        return {"answer": None, "error": resp.get("error", "unknown error")}
    return {"answer": resp.get("response", "")}

# ── nitpick_ref.md section index ─────────────────────────────────────────────

def _build_section_index(path: str) -> list[dict]:
    sections: list[dict] = []
    if not os.path.isfile(path): return sections
    with open(path) as f: raw = f.read()
    parts = re.split(r'^(##[^\n]*)', raw, flags=re.MULTILINE)
    for i in range(1, len(parts) - 1, 2):
        sections.append({"heading": parts[i].strip(), "body": parts[i + 1].strip()})
    return sections

_SECTION_INDEX: list[dict] = []

def _get_sections() -> list[dict]:
    global _SECTION_INDEX
    if not _SECTION_INDEX: _SECTION_INDEX = _build_section_index(NITPICK_REF_MD)
    return _SECTION_INDEX

# ── tool: nitpick_compile ────────────────────────────────────────────────────

def nitpick_compile(source: str) -> dict:
    if not NITPICKC_BIN:
        return {"success": False, "errors": [{"message": "npkc binary not found"}], "warnings": [], "output": ""}
    with tempfile.NamedTemporaryFile(suffix=".npk", mode="w", delete=False, encoding="utf-8") as f:
        f.write(source)
        src_path = f.name
    out_path = src_path + ".out"
    try:
        proc = subprocess.run([NITPICKC_BIN, src_path, "-o", out_path], capture_output=True, text=True, timeout=30, env={**os.environ, "NO_COLOR": "1"})
        errors: list[dict] = []
        warnings: list[dict] = []
        ansi_re = re.compile(r'\x1b\[[0-9;]*[mGKHF]')
        diag_re = re.compile(r'^(?:(.+?):(\d+)(?::(\d+))?:\s*)?(error|warning|note):\s*(.+)$', re.IGNORECASE)
        for line in (proc.stderr + proc.stdout).splitlines():
            clean = ansi_re.sub('', line).strip()
            m = diag_re.match(clean)
            if m:
                entry: dict = {"message": m.group(5)}
                if m.group(2): entry["line"] = int(m.group(2))
                if m.group(3): entry["column"] = int(m.group(3))
                severity = m.group(4).lower()
                if severity == "error": errors.append(entry)
                else: warnings.append(entry)
            elif clean:
                l = clean.lower()
                entry = {"message": clean}
                if "error" in l: errors.append(entry)
                elif "warning" in l or "warn" in l: warnings.append(entry)
                else: (errors if proc.returncode != 0 else warnings).append(entry)
        return {"success": proc.returncode == 0, "errors": errors, "warnings": warnings, "output": proc.stdout.strip()}
    except subprocess.TimeoutExpired:
        return {"success": False, "errors": [{"message": "compiler timed out"}], "warnings": [], "output": ""}
    finally:
        try: os.unlink(src_path)
        except OSError: pass
        try: os.unlink(out_path)
        except OSError: pass

# ── tool: nitpick_check ─────────────────────────────────────────────────────

_FINDING_RE = re.compile(r'^(.+?):(\d+):\s+\[([A-Z_]+)\]\s+(.+)$')

def nitpick_check(source: str) -> dict:
    if not SAFETY_BIN:
        return {"issues": [], "error": "nitpick-safety binary not found"}
    with tempfile.NamedTemporaryFile(suffix=".npk", mode="w", delete=False, encoding="utf-8") as f:
        f.write(source)
        src_path = f.name
    try:
        proc = subprocess.run([SAFETY_BIN, src_path], capture_output=True, text=True, timeout=10)
        issues: list[dict] = []
        for line in proc.stdout.splitlines():
            line = line.strip()
            if not line: continue
            m = _FINDING_RE.match(line)
            if m: issues.append({"line": int(m.group(2)), "tag": m.group(3), "message": m.group(4)})
            else: issues.append({"line": 0, "tag": "INFO", "message": line})
        return {"issues": issues}
    except subprocess.TimeoutExpired:
        return {"issues": [], "error": "nitpick-safety timed out"}
    finally:
        try: os.unlink(src_path)
        except OSError: pass

# ── tool: nitpick_format ─────────────────────────────────────────────────────

def nitpick_format(source: str) -> dict:
    """Enhanced Nitpick source code formatter."""
    lines = source.splitlines()
    result: list[str] = []
    indent = 0
    indent_str = "    "
    openers = {"func", "struct", "enum", "trait", "impl", "Type", "if", "else", "while", "for", "loop", "till", "when", "pick", "failsafe", "extern", "defer", "match"}
    
    for raw_line in lines:
        stripped = raw_line.strip()
        
        # Collapse multiple spaces around =
        stripped = re.sub(r'\s*=\s*', ' = ', stripped)
        
        # Ensure spaces after commas
        stripped = re.sub(r',\s*', ', ', stripped)
        
        # Decrease indent for closing braces
        if stripped in ("}", "};", "end", "]", ");"):
            indent = max(0, indent - 1)
        elif stripped.startswith("}"):
            indent = max(0, indent - 1)

        if stripped:
            result.append(indent_str * indent + stripped)
        else:
            result.append("")

        if stripped.endswith("{") or stripped.endswith("[") or stripped.endswith("("):
            indent += 1
        elif any(stripped.startswith(op + " ") or stripped.startswith(op + "(") or stripped == op for op in openers):
            if not stripped.endswith("}") and not stripped.endswith("};"):
                if "{" not in stripped:
                    pass
                    
    formatted = "\n".join(result)
    if source.endswith("\n"):
        formatted += "\n"
    return {"formatted": formatted}

def nitpick_docs(query: str) -> dict:
    sections = _get_sections()
    if not sections: return {"excerpt": f"nitpick_ref.md not found"}
    terms = [t for t in re.split(r'\s+', query.lower().strip()) if t]
    if not terms: return {"excerpt": "Empty query"}
    scored: list[tuple[int, int, dict]] = []
    for idx, sec in enumerate(sections):
        h = sec["heading"].lower()
        b = sec["body"].lower()
        score = sum(h.count(t) * 3 + b.count(t) for t in terms)
        if score > 0: scored.append((score, idx, sec))
    if not scored: return {"excerpt": f"No matches found"}
    scored.sort(key=lambda x: -x[0])
    parts: list[str] = []
    for _, _, sec in scored[:3]:
        lines = (sec["heading"] + "\n\n" + sec["body"]).splitlines()
        chunk = "\n".join(lines[:40])
        if len(lines) > 40: chunk += f"\n\n... ({len(lines) - 40} more lines)"
        parts.append(chunk)
    return {"excerpt": "\n\n---\n\n".join(parts)}

def nitpick_scaffold(path: str) -> dict:
    try:
        os.makedirs(os.path.join(path, "src"), exist_ok=True)
        with open(os.path.join(path, "src", "main.npk"), "w") as f:
            f.write("pub func:main = int32() {\n    println(\"Hello, Nitpick!\");\n    return 0i32;\n};\n")
        with open(os.path.join(path, "nitpick-package.toml"), "w") as f:
            f.write("[package]\nname = \"my_project\"\nversion = \"0.1.0\"\n")
        return {"success": True, "output": f"Scaffolded Nitpick project in {path}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def nitpick_run(source: str) -> dict:
    if not NITPICKC_BIN: return {"success": False, "compiler_output": "npkc not found", "run_output": ""}
    with tempfile.NamedTemporaryFile(suffix=".npk", mode="w", delete=False) as f:
        f.write(source)
        src_path = f.name
    out_path = src_path + ".out"
    try:
        cproc = subprocess.run([NITPICKC_BIN, src_path, "-o", out_path], capture_output=True, text=True, timeout=30)
        if cproc.returncode != 0: return {"success": False, "compiler_output": cproc.stderr + cproc.stdout, "run_output": ""}
        rproc = subprocess.run([out_path], capture_output=True, text=True, timeout=10)
        return {"success": rproc.returncode == 0, "compiler_output": cproc.stderr + cproc.stdout, "run_output": rproc.stdout + rproc.stderr}
    except Exception as e:
        return {"success": False, "compiler_output": str(e), "run_output": ""}
    finally:
        try: os.unlink(src_path)
        except: pass
        try: os.unlink(out_path)
        except: pass

# ── MCP JSON-RPC 2.0 protocol ─────────────────────────────────────────────

TOOL_DEFINITIONS = [
    {
        "name": "nitpick_compile",
        "description": "Compile Nitpick source code.",
        "inputSchema": {"type": "object", "properties": {"source": {"type": "string"}}, "required": ["source"]},
    },
    {
        "name": "nitpick_check",
        "description": "Run the nitpick-safety static audit tool.",
        "inputSchema": {"type": "object", "properties": {"source": {"type": "string"}}, "required": ["source"]},
    },
    {
        "name": "nitpick_docs",
        "description": "Search the Nitpick language reference card.",
        "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
    },
    {
        "name": "nitpick_format",
        "description": "Format Nitpick source code.",
        "inputSchema": {"type": "object", "properties": {"source": {"type": "string"}}, "required": ["source"]},
    },
    {
        "name": "nitpick_scaffold",
        "description": "Scaffolds a new Nitpick project structure.",
        "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}
    },
    {
        "name": "nitpick_run",
        "description": "Compile and run a Nitpick source file.",
        "inputSchema": {"type": "object", "properties": {"source": {"type": "string"}}, "required": ["source"]}
    }
]

SERVER_INFO  = {"name": "nitpick-mcp", "version": "0.3.4"}
CAPABILITIES = {"tools": {}, "resources": {}}

def _handle(req: dict) -> dict | None:
    method = req.get("method", "")
    rid    = req.get("id")
    params = req.get("params") or {}
    def ok(result): return {"jsonrpc": "2.0", "id": rid, "result": result} if rid is not None else None
    def err(code, message): return {"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": message}}

    if method == "initialize": return ok({"protocolVersion": "2024-11-05", "serverInfo": SERVER_INFO, "capabilities": CAPABILITIES})
    if method in ("notifications/initialized", "initialized"): return None
    if method == "ping": return ok({})

    if method == "tools/list": return ok({"tools": TOOL_DEFINITIONS})
    if method == "tools/call":
        name = params.get("name", "")
        args = params.get("arguments") or {}
        if name == "nitpick_compile": return ok({"content": [{"type": "text", "text": json.dumps(nitpick_compile(args.get("source", "")), indent=2)}]})
        if name == "nitpick_check": return ok({"content": [{"type": "text", "text": json.dumps(nitpick_check(args.get("source", "")), indent=2)}]})
        if name == "nitpick_docs": return ok({"content": [{"type": "text", "text": nitpick_docs(args.get("query", ""))["excerpt"]}]})
        if name == "nitpick_format": return ok({"content": [{"type": "text", "text": json.dumps(nitpick_format(args.get("source", "")), indent=2)}]})
        if name == "nitpick_scaffold": return ok({"content": [{"type": "text", "text": json.dumps(nitpick_scaffold(args.get("path", "")), indent=2)}]})
        if name == "nitpick_run": return ok({"content": [{"type": "text", "text": json.dumps(nitpick_run(args.get("source", "")), indent=2)}]})
        return err(-32601, f"Unknown tool: {name}")

    if rid is not None: return err(-32601, f"Method not found: {method}")
    return None

def main() -> None:
    log = lambda msg: print(f"[nitpick-mcp] {msg}", file=sys.stderr, flush=True)
    log(f"nitpickc      = {NITPICKC_BIN or '(not found)'}")
    log(f"nitpick-safety= {SAFETY_BIN or '(not found)'}")
    log("ready — waiting for JSON-RPC requests on stdin")

    for raw in sys.stdin:
        raw = raw.strip()
        if not raw: continue
        try: req = json.loads(raw)
        except json.JSONDecodeError as exc:
            print(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": f"Parse error: {exc}"}}), flush=True)
            continue
        try: resp = _handle(req)
        except Exception as exc: resp = {"jsonrpc": "2.0", "id": req.get("id"), "error": {"code": -32603, "message": f"Internal error: {exc}"}}
        if resp is not None: print(json.dumps(resp), flush=True)

if __name__ == "__main__":
    main()
