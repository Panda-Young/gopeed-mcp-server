"""
Gopeed MCP Server — thin wrapper for development.

When installed as a package, use `gopeed-mcp-server` command directly.
This file allows running `python server.py` from the repo root.
"""

from __future__ import annotations

import os
import sys

# Ensure the src/ package is importable when running from repo root
_src = os.path.join(os.path.dirname(__file__), "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

from gopeed_mcp_server.server import main  # noqa: E402

if __name__ == "__main__":
    main()
