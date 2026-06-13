#!/usr/bin/env python3
"""
aria-mcp — MCP stdio server for the Nitpick language toolchain.

Transport : stdio (JSON-RPC 2.0, newline-delimited)
Zero deps : pure Python 3.8+ stdlib only

Tools:
  aria_compile(source)            — compile Nitpick source via ariac, structured result
  aria_check(source)              — run aria-safety audit, structured findings
  aria_docs(query)                — section-level search over aria_ref.md
  aria_format(source)             — basic indentation/whitespace normalizer
  aria_ask(question[, context])   — query the Nitpick specialist fine-tuned model
                                    (optional; requires specialist server to be
                                     available at SPECIALIST_SCRIPT / PATH)

Binary discovery order (for ariac and aria-safety):
  1. Environment variable  ARIAC_BIN / ARIA_SAFETY_BIN
  2. <repo-root>/build/ariac   or   <repo-root>/tools/aria-safety/aria-safety
  3. $PATH

Specialist server discovery:
  1. SPECIALIST_SCRIPT env var (path to aria_specialist_server.py)
  2. <repo-root>/tools/aria_specialist_server.py
Set ARIA_ASK_DISABLED=1 to suppress the tool from the tools/list entirely.
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

# ── binary / path resolution ──────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent
# aria-mcp/ sits inside aria-tools repo, but ariac lives in the aria repo.
# Try the sibling-repo layout first: REPOS/aria/build/ariac
REPO_ROOT   = SCRIPT_DIR.parent.parent  # aria-tools/aria-mcp/ → aria-tools/ → REPOS/
ARIA_ROOT   = REPO_ROOT / "aria"         # REPOS/aria/


def _find_bin(env_var: str, *candidates: Path) -> str | None:
    v = os.environ.get(env_var)
    if v and Path(v).is_file() and os.access(v, os.X_OK):
        return v
    for c in candidates:
        if c.is_file() and os.access(c, os.X_OK):
            return str(c)
    return None


ARIAC_BIN   = _find_bin("ARIAC_BIN",
                         ARIA_ROOT / "build" / "ariac",
                         REPO_ROOT / "build" / "ariac") \
              or shutil.which("ariac")

SAFETY_BIN  = _find_bin("ARIA_SAFETY_BIN",
                         SCRIPT_DIR.parent / "aria-safety" / "aria-safety",
                         REPO_ROOT / "tools" / "aria-safety" / "aria-safety") \
              or shutil.which("aria-safety")


def _find_ref_md() -> str:
    """Resolve aria_ref.md: env var → common locations → fallback."""
    env = os.environ.get("ARIA_REF_MD")
    if env and Path(env).is_file():
        return env
    candidates = [
        REPO_ROOT / "aria-docs" / "reference" / "aria_ref.md",
        REPO_ROOT / ".internal" / "aria_ref.md",
        ARIA_ROOT / "docs" / "aria_ref.md",
    ]
    for c in candidates:
        if c.is_file():
            return str(c)
    return str(candidates[0])  # default even if missing


ARIA_REF_MD = _find_ref_md()

SPECIALIST_SCRIPT = (
    os.environ.get("SPECIALIST_SCRIPT")
    or str(REPO_ROOT / "aria-specialist" / "aria_specialist_server.py")
)
ARIA_ASK_DISABLED = os.environ.get("ARIA_ASK_DISABLED", "").strip() not in ("", "0")

# ── aria_ask: specialist model proxy ────────────────────────────────────────

READY_TIMEOUT = 240   # seconds; loading a 7B model can take a while


class _SpecialistProxy:
    """
    Lazy-starting, long-lived proxy to aria_specialist_server.py.
    Thread-safe (single-threaded server; only one generation at a time anyway).
    The subprocess is started on the first aria_ask call and kept alive
    for the lifetime of the MCP server process.
    """

    def __init__(self) -> None:
        self._proc: subprocess.Popen | None = None
        self._lock  = threading.Lock()
        self._req_id = 0
        self._ready  = False

    def _start(self) -> str | None:
        """Start the specialist subprocess.  Returns an error string on failure."""
        if not os.path.isfile(SPECIALIST_SCRIPT):
            return f"specialist server not found: {SPECIALIST_SCRIPT}"

        try:
            self._proc = subprocess.Popen(
                [sys.executable, SPECIALIST_SCRIPT],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
        except OSError as exc:
            return f"failed to start specialist server: {exc}"

        # Wait for the {"ready":true} handshake line
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
                    return None  # success
            except json.JSONDecodeError:
                pass  # skip non-JSON lines (diagnostics etc.)

        self._proc.kill()
        return f"specialist server did not become ready within {READY_TIMEOUT} s"

    def ask(self, question: str, context: str = "",
            max_tokens: int = 512, temperature: float = 0.2) -> dict:
        with self._lock:
            # Ensure the subprocess is alive
            if self._proc is None or self._proc.poll() is not None:
                self._ready = False
                err = self._start()
                if err:
                    return {"ok": False, "error": err}

            self._req_id += 1
            req = json.dumps({
                "id":          self._req_id,
                "instruction": question,
                "context":     context,
                "max_tokens":  max_tokens,
                "temperature": temperature,
            })
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
                resp = json.loads(line)
                return resp  # { id, ok, response } or { id, ok, error }
            except json.JSONDecodeError as exc:
                return {"ok": False, "error": f"malformed response from specialist: {exc}"}


_SPECIALIST = _SpecialistProxy()


def aria_ask(question: str, context: str = "",
             max_tokens: int = 512, temperature: float = 0.2) -> dict:
    resp = _SPECIALIST.ask(question, context, max_tokens, temperature)
    if not resp.get("ok"):
        return {"answer": None, "error": resp.get("error", "unknown error")}
    return {"answer": resp.get("response", "")}


# ── aria_ref.md section index ─────────────────────────────────────────────

def _build_section_index(path: str) -> list[dict]:
    """
    Parse aria_ref.md into sections keyed by their ## heading.
    Returns list of { "heading": str, "body": str } dicts.
    """
    sections: list[dict] = []
    if not os.path.isfile(path):
        return sections

    with open(path) as f:
        raw = f.read()

    parts = re.split(r'^(##[^\n]*)', raw, flags=re.MULTILINE)
    # parts[0] is pre-first-heading text, then alternating heading / body
    for i in range(1, len(parts) - 1, 2):
        sections.append({
            "heading": parts[i].strip(),
            "body":    parts[i + 1].strip(),
        })
    return sections


_SECTION_INDEX: list[dict] = []  # lazy-loaded on first aria_docs call


def _get_sections() -> list[dict]:
    global _SECTION_INDEX
    if not _SECTION_INDEX:
        _SECTION_INDEX = _build_section_index(ARIA_REF_MD)
    return _SECTION_INDEX

# ── tool: aria_compile ────────────────────────────────────────────────────

def aria_compile(source: str) -> dict:
    if not ARIAC_BIN:
        return {
            "success":  False,
            "errors":   [{"message": "ariac binary not found — set ARIAC_BIN env var or add to $PATH"}],
            "warnings": [],
            "output":   "",
        }

    with tempfile.NamedTemporaryFile(suffix=".aria", mode="w",
                                     delete=False, encoding="utf-8") as f:
        f.write(source)
        src_path = f.name

    out_path = src_path + ".out"
    try:
        proc = subprocess.run(
            [ARIAC_BIN, src_path, "-o", out_path],
            capture_output=True, text=True, timeout=30,
            env={**os.environ, "NO_COLOR": "1"},
        )
        errors: list[dict]   = []
        warnings: list[dict] = []

        # Strip ANSI escape sequences from compiler output
        ansi_re = re.compile(r'\x1b\[[0-9;]*[mGKHF]')

        # Match patterns like "file.aria:10:5: error: message" or "error: message"
        diag_re = re.compile(r'^(?:(.+?):(\d+)(?::(\d+))?:\s*)?'
                             r'(error|warning|note):\s*(.+)$', re.IGNORECASE)

        for line in (proc.stderr + proc.stdout).splitlines():
            clean = ansi_re.sub('', line).strip()
            m = diag_re.match(clean)
            if m:
                entry: dict = {"message": m.group(5)}
                if m.group(2):
                    entry["line"] = int(m.group(2))
                if m.group(3):
                    entry["column"] = int(m.group(3))
                severity = m.group(4).lower()
                if severity == "error":
                    errors.append(entry)
                else:
                    warnings.append(entry)
            elif clean:
                l = clean.lower()
                entry = {"message": clean}
                if "error" in l:
                    errors.append(entry)
                elif "warning" in l or "warn" in l:
                    warnings.append(entry)
                else:
                    (errors if proc.returncode != 0 else warnings).append(entry)

        return {
            "success":  proc.returncode == 0,
            "errors":   errors,
            "warnings": warnings,
            "output":   proc.stdout.strip(),
        }

    except subprocess.TimeoutExpired:
        return {
            "success":  False,
            "errors":   [{"message": "compiler timed out (> 30 s)"}],
            "warnings": [],
            "output":   "",
        }
    finally:
        try:
            os.unlink(src_path)
        except OSError:
            pass
        try:
            os.unlink(out_path)
        except OSError:
            pass

# ── tool: aria_check ─────────────────────────────────────────────────────

# Matches:  file.aria:42: [TAG] message description
_FINDING_RE = re.compile(r'^(.+?):(\d+):\s+\[([A-Z_]+)\]\s+(.+)$')


def aria_check(source: str) -> dict:
    if not SAFETY_BIN:
        return {
            "issues": [],
            "error":  "aria-safety binary not found — set ARIA_SAFETY_BIN env var or add to $PATH",
        }

    with tempfile.NamedTemporaryFile(suffix=".aria", mode="w",
                                     delete=False, encoding="utf-8") as f:
        f.write(source)
        src_path = f.name

    try:
        proc = subprocess.run(
            [SAFETY_BIN, src_path],
            capture_output=True, text=True, timeout=10,
        )
        issues: list[dict] = []
        for line in proc.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            m = _FINDING_RE.match(line)
            if m:
                issues.append({
                    "line":    int(m.group(2)),
                    "tag":     m.group(3),
                    "message": m.group(4),
                })
            else:
                issues.append({"line": 0, "tag": "INFO", "message": line})

        return {"issues": issues}

    except subprocess.TimeoutExpired:
        return {"issues": [], "error": "aria-safety timed out"}
    finally:
        try:
            os.unlink(src_path)
        except OSError:
            pass

# ── tool: aria_format ─────────────────────────────────────────────────────

def aria_format(source: str) -> dict:
    """Basic Nitpick source code formatter: normalizes indentation and whitespace."""
    lines = source.splitlines()
    result: list[str] = []
    indent = 0
    indent_str = "    "  # 4 spaces

    # Keywords that increase indentation
    openers = {"func", "struct", "enum", "trait", "impl", "Type", "if", "else",
               "while", "for", "loop", "till", "when", "pick", "failsafe",
               "extern", "defer"}

    for raw_line in lines:
        stripped = raw_line.strip()

        # Decrease indent for closing braces/end
        if stripped in ("}", "};", "end"):
            indent = max(0, indent - 1)

        if stripped:
            result.append(indent_str * indent + stripped)
        else:
            result.append("")

        # Increase indent after lines ending with { or containing opener keywords
        if stripped.endswith("{"):
            indent += 1
        elif any(stripped.startswith(op + " ") or stripped.startswith(op + "(")
                 or stripped == op for op in openers):
            # Only if line doesn't also close on same line
            if not stripped.endswith("}") and not stripped.endswith("};"):
                if "{" not in stripped:
                    pass  # opener keyword without brace — don't indent yet

    formatted = "\n".join(result)
    if source.endswith("\n"):
        formatted += "\n"

    return {"formatted": formatted}


def aria_docs(query: str) -> dict:
    sections = _get_sections()
    if not sections:
        return {"excerpt": f"aria_ref.md not found or empty (path: {ARIA_REF_MD})"}

    terms = [t for t in re.split(r'\s+', query.lower().strip()) if t]
    if not terms:
        return {"excerpt": "Empty query — provide search terms, e.g. 'result propagation' or 'pointer system'"}

    # Score each section by weighted term hits:
    #   heading match counts 3×, body match counts 1× per term per occurrence
    scored: list[tuple[int, int, dict]] = []  # (score, original_index, section)
    for idx, sec in enumerate(sections):
        h = sec["heading"].lower()
        b = sec["body"].lower()
        score = 0
        for t in terms:
            score += h.count(t) * 3
            score += b.count(t)
        if score > 0:
            scored.append((score, idx, sec))

    if not scored:
        return {"excerpt": f"No matches found for: {query!r}"}

    scored.sort(key=lambda x: -x[0])

    # Return top 3 sections (truncated to 40 lines each to keep responses manageable)
    parts: list[str] = []
    for _, _, sec in scored[:3]:
        lines = (sec["heading"] + "\n\n" + sec["body"]).splitlines()
        chunk = "\n".join(lines[:40])
        if len(lines) > 40:
            chunk += f"\n\n... ({len(lines) - 40} more lines — query aria_docs more specifically)"
        parts.append(chunk)

    return {"excerpt": "\n\n---\n\n".join(parts)}

# ── tool: nitpick_scaffold ────────────────────────────────────────────────
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

# ── tool: nitpick_run ─────────────────────────────────────────────────────
def nitpick_run(source: str) -> dict:
    if not ARIAC_BIN:
        return {"success": False, "compiler_output": "npkc not found", "run_output": ""}
    with tempfile.NamedTemporaryFile(suffix=".npk", mode="w", delete=False) as f:
        f.write(source)
        src_path = f.name
    out_path = src_path + ".out"
    try:
        cproc = subprocess.run([ARIAC_BIN, src_path, "-o", out_path], capture_output=True, text=True, timeout=30)
        if cproc.returncode != 0:
            return {"success": False, "compiler_output": cproc.stderr + cproc.stdout, "run_output": ""}
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
        "name": "aria_compile",
        "description": (
            "Compile Nitpick source code using the ariac compiler. "
            "Returns { success, errors[], warnings[], output }. "
            "Nitpick uses a Result<T> type system — all user-defined functions implicitly "
            "return Result<T>. Use aria_docs to look up syntax before writing code."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "source": {
                    "type":        "string",
                    "description": "Complete Nitpick source code to compile.",
                }
            },
            "required": ["source"],
        },
    },
    {
        "name": "aria_check",
        "description": (
            "Run the aria-safety static audit tool on Nitpick source code. "
            "Returns { issues: [{ line, tag, message }] }. "
            "Tags: [WILD] manual memory, [RAW] raw() Result bypass, "
            "[DROP] discarded Result<T>, [OK] unknown type bypass, "
            "[WEAK_CAS] weak CAS must be in retry loop, "
            "[RELAXED] relaxed atomic ordering, "
            "[FAILSAFE] empty or trivial failsafe block."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "source": {
                    "type":        "string",
                    "description": "Nitpick source code to audit for safety issues.",
                }
            },
            "required": ["source"],
        },
    },
    {
        "name": "aria_docs",
        "description": (
            "Search the Nitpick language reference card (aria_ref.md) for documentation "
            "on any type, operator, or language construct. "
            "Returns relevant section excerpts. "
            "Example queries: 'result propagation', 'pointer system', "
            "'string interpolation', 'atomic operations', 'control flow', "
            "'wild allocation', 'failsafe block', 'generics contracts'."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type":        "string",
                    "description": "Terms to search for in the Nitpick language reference.",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "aria_format",
        "description": (
            "Format Nitpick source code — normalize indentation and whitespace. "
            "Returns { formatted: string } with consistently indented code."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "source": {
                    "type":        "string",
                    "description": "Nitpick source code to format.",
                }
            },
            "required": ["source"],
        },
    },
    {
        "name": "nitpick_scaffold",
        "description": "Scaffolds a new Nitpick project structure.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to create the project in"}
            },
            "required": ["path"]
        }
    },
    {
        "name": "nitpick_run",
        "description": "Compile and run a Nitpick source file.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source": {"type": "string", "description": "Nitpick source code"}
            },
            "required": ["source"]
        }
    }
] + ([] if ARIA_ASK_DISABLED else [
    {
        "name": "aria_ask",
        "description": (
            "Ask the Nitpick language specialist fine-tuned model a question about "
            "Nitpick syntax, idioms, or how to write specific code. "
            "Returns the model's text response, which often contains Nitpick code. "
            "Validate generated code with aria_compile and audit with aria_check. "
            "The specialist server loads a ~7B parameter model on first use and "
            "may take 1-3 minutes to warm up. Subsequent calls are fast. "
            "Set ARIA_ASK_DISABLED=1 to hide this tool if the model is not available."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "question": {
                    "type":        "string",
                    "description": "What to ask the Nitpick specialist — a task, question, or code request.",
                },
                "context": {
                    "type":        "string",
                    "description": "Optional: existing Nitpick code or context to provide alongside the question.",
                },
                "max_tokens": {
                    "type":        "integer",
                    "description": "Maximum tokens to generate (default 512).",
                },
                "temperature": {
                    "type":        "number",
                    "description": "Sampling temperature 0.0-1.0 (default 0.2 for consistent code).",
                },
            },
            "required": ["question"],
        },
    },
])

SERVER_INFO  = {"name": "aria-mcp", "version": "0.3.3"}
CAPABILITIES = {"tools": {}, "resources": {}}


def _handle(req: dict) -> dict | None:
    method = req.get("method", "")
    rid    = req.get("id")          # None for notifications
    params = req.get("params") or {}

    def ok(result: object) -> dict | None:
        if rid is None:
            return None
        return {"jsonrpc": "2.0", "id": rid, "result": result}

    def err(code: int, message: str, data: object = None) -> dict:
        e: dict = {"code": code, "message": message}
        if data is not None:
            e["data"] = data
        return {"jsonrpc": "2.0", "id": rid, "error": e}

    # ── handshake ─────────────────────────────────────────────
    if method == "initialize":
        return ok({
            "protocolVersion": "2024-11-05",
            "serverInfo":      SERVER_INFO,
            "capabilities":    CAPABILITIES,
        })

    if method in ("notifications/initialized", "initialized"):
        return None  # notification — no response

    if method == "ping":
        return ok({})

    # ── resources ──────────────────────────────────────────────
    if method == "resources/list":
        sections = _get_sections()
        resources = []
        for i, sec in enumerate(sections):
            heading = sec["heading"].strip().lstrip("#").strip()
            resources.append({
                "uri": f"aria://ref/{i}",
                "name": heading,
                "mimeType": "text/markdown",
            })
        return ok({"resources": resources})

    if method == "resources/read":
        uri = params.get("uri", "")
        if uri.startswith("aria://ref/"):
            try:
                idx = int(uri.split("/")[-1])
                sections = _get_sections()
                if 0 <= idx < len(sections):
                    sec = sections[idx]
                    text = sec["heading"] + "\n\n" + sec["body"]
                    return ok({"contents": [{"uri": uri, "mimeType": "text/markdown", "text": text}]})
            except (ValueError, IndexError):
                pass
            return err(-32602, f"Resource not found: {uri}")
        return err(-32602, f"Unknown resource URI scheme: {uri}")

    # ── tools ─────────────────────────────────────────────────
    if method == "tools/list":
        return ok({"tools": TOOL_DEFINITIONS})

    if method == "tools/call":
        name = params.get("name", "")
        args = params.get("arguments") or {}

        if name == "nitpick_compile" or name == "aria_compile":
            r    = aria_compile(args.get("source", ""))
            text = json.dumps(r, indent=2)
            return ok({"content": [{"type": "text", "text": text}]})

        if name == "nitpick_check" or name == "aria_check":
            r    = aria_check(args.get("source", ""))
            text = json.dumps(r, indent=2)
            return ok({"content": [{"type": "text", "text": text}]})

        if name == "nitpick_docs" or name == "aria_docs":
            r = aria_docs(args.get("query", ""))
            return ok({"content": [{"type": "text", "text": r["excerpt"]}]})

        if name == "nitpick_format" or name == "aria_format":
            r = aria_format(args.get("source", ""))
            text = json.dumps(r, indent=2)
            return ok({"content": [{"type": "text", "text": text}]})

        if name == "nitpick_scaffold":
            r = nitpick_scaffold(args.get("path", ""))
            text = json.dumps(r, indent=2)
            return ok({"content": [{"type": "text", "text": text}]})

        if name == "nitpick_run":
            r = nitpick_run(args.get("source", ""))
            text = json.dumps(r, indent=2)
            return ok({"content": [{"type": "text", "text": text}]})

        if name == "nitpick_ask" or name == "aria_ask":
            if ARIA_ASK_DISABLED:
                return err(-32601, "aria_ask is disabled (ARIA_ASK_DISABLED=1)")
            r    = aria_ask(
                args.get("question", ""),
                args.get("context", ""),
                int(args.get("max_tokens", 512)),
                float(args.get("temperature", 0.2)),
            )
            text = r.get("answer") or f"[error] {r.get('error', 'no response')}"
            return ok({"content": [{"type": "text", "text": text}]})

        return err(-32601, f"Unknown tool: {name!r}")

    # ── fallback ───────────────────────────────────────────────
    if rid is not None:
        return err(-32601, f"Method not found: {method!r}")
    return None   # unknown notification — silently ignore


# ── stdio loop ────────────────────────────────────────────────────────────

def main() -> None:
    log = lambda msg: print(f"[nitpick-mcp] {msg}", file=sys.stderr, flush=True)
    log(f"ariac      = {ARIAC_BIN or '(not found)'}")
    log(f"aria-safety= {SAFETY_BIN or '(not found)'}")
    log(f"aria_ref   = {ARIA_REF_MD}")
    log(f"aria_ask   = {'disabled' if ARIA_ASK_DISABLED else SPECIALIST_SCRIPT}")
    log("ready — waiting for JSON-RPC requests on stdin")

    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue

        try:
            req = json.loads(raw)
        except json.JSONDecodeError as exc:
            resp: dict = {
                "jsonrpc": "2.0",
                "id":      None,
                "error":   {"code": -32700, "message": f"Parse error: {exc}"},
            }
            print(json.dumps(resp), flush=True)
            continue

        try:
            resp = _handle(req)
        except Exception as exc:
            resp = {
                "jsonrpc": "2.0",
                "id":      req.get("id"),
                "error":   {"code": -32603, "message": f"Internal error: {exc}"},
            }

        if resp is not None:
            print(json.dumps(resp), flush=True)


if __name__ == "__main__":
    main()
