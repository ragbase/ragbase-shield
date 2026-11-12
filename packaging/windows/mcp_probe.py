"""MCP stdio handshake against the installed Shield (test_install.ps1, step W5; same client as test_payload.sh 6.6).

Usage (run by the installed runtime, isolated):
  python.exe -I mcp_probe.py <python.exe of the install> <claude-desktop manifest.json>

Starts "<python.exe> -I -X utf8 -m ragbase_shield mcp" (the command install.json gives MCP apps), sends
initialize, notifications/initialized and tools/list, and compares the tool names with the .mcpb manifest.
Prints the two sorted lists; exit 0 when they are equal. The data folder comes from the caller's environment
(test_install.ps1 sets a temporary RAGBASE_SHIELD_HOME and RAGBASE_SHIELD_KEYRING=0).
"""
import json
import subprocess
import sys
import threading

exe, manifest = sys.argv[1], sys.argv[2]
with open(manifest, encoding="utf-8") as f:
    expected = sorted(t["name"] for t in json.load(f)["tools"])
p = subprocess.Popen([exe, "-I", "-X", "utf8", "-m", "ragbase_shield", "mcp"], stdin=subprocess.PIPE,
                     stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding="utf-8")
timer = threading.Timer(120, p.kill)
timer.start()


def send(m):
    p.stdin.write(json.dumps(m) + "\n")
    p.stdin.flush()


def read(i):
    for line in p.stdout:
        try:
            m = json.loads(line)
        except ValueError:
            continue
        if m.get("id") == i:
            return m
    return {}


send({"jsonrpc": "2.0", "id": 1, "method": "initialize",
      "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "msitest", "version": "0"}}})
init = read(1)
send({"jsonrpc": "2.0", "method": "notifications/initialized"})
send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
tools = sorted(t["name"] for t in read(2).get("result", {}).get("tools", []))
p.stdin.close()
try:
    p.wait(timeout=30)
except subprocess.TimeoutExpired:
    p.kill()
timer.cancel()
server = init.get("result", {}).get("serverInfo", {})
print("server:", server.get("name"), server.get("version"), "protocol", init.get("result", {}).get("protocolVersion"))
print("server tools:", tools)
print("manifest tools:", expected)
sys.exit(0 if tools and tools == expected else 1)
