"""RAGbase Shield launcher for the Claude Desktop extension (MCPB, server.type "uv").

build_mcpb.sh copies this file to <bundle>/src/server.py, next to a copy of the
ragbase_shield package (<bundle>/src/ragbase_shield). Claude Desktop runs it with
"uv run --directory <bundle> src/server.py"; uv installs the dependencies listed in the
bundle's pyproject.toml. This file only starts the same stdio MCP server as
"ragbase-shield mcp". It writes nothing to stdout itself (stdout is the MCP channel).
"""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))


def main() -> int:
    from ragbase_shield.cli import main as cli_main

    sys.argv = ["ragbase-shield", "mcp"]
    result = cli_main()
    return int(result or 0)


if __name__ == "__main__":
    sys.exit(main())
