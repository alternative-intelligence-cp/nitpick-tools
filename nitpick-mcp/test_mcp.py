#!/usr/bin/env python3
import sys
import json
import subprocess
import time

mcp_script = "./nitpick_mcp.py"

p = subprocess.Popen(
    ["python3", mcp_script],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

def send_request(method, params, req_id):
    req = {
        "jsonrpc": "2.0",
        "id": req_id,
        "method": method,
        "params": params
    }
    p.stdin.write(json.dumps(req) + "\n")
    p.stdin.flush()
    line = p.stdout.readline()
    if not line:
        return None
    return json.loads(line)

try:
    print("Testing initialize...")
    res = send_request("initialize", {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name":"test","version":"1"}}, 1)
    assert res is not None, "Failed to get response"
    assert "result" in res, f"Expected result in {res}"

    # After initialize, the server sends an initialized notification?
    # Actually client sends initialized notification.
    notif = {
        "jsonrpc": "2.0",
        "method": "notifications/initialized",
        "params": {}
    }
    p.stdin.write(json.dumps(notif) + "\n")
    p.stdin.flush()

    print("Testing tools/list...")
    res = send_request("tools/list", {}, 2)
    assert res is not None, "Failed to get response"
    assert "result" in res, f"Expected result in {res}"
    tools = res["result"]["tools"]
    tool_names = [t["name"] for t in tools]
    assert "nitpick_compile" in tool_names
    assert "nitpick_check" in tool_names
    assert "nitpick_docs" in tool_names

    print("All MCP tests passed!")
finally:
    p.terminate()
