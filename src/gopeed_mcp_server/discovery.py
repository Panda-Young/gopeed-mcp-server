"""
Port auto-discovery for Gopeed.

When Gopeed uses random ports (default), this module locates the actual
listening port by scanning netstat output and verifying the API endpoint.
"""

from __future__ import annotations

import os
import subprocess


def find_gopeed_ports() -> list[str]:
    """Return ordered list of ports on which gopeed is listening on 127.0.0.1."""
    try:
        out = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=10,
        ).stdout
    except Exception:
        return []

    pids = _find_gopeed_pids()
    ports: list[str] = []
    for line in out.splitlines():
        if "LISTENING" not in line or "127.0.0.1:" not in line:
            continue
        parts = line.split()
        if len(parts) < 5:
            continue
        addr = parts[1]
        pid = parts[-1]
        if pids and pid not in pids:
            continue
        port = addr.split(":")[-1]
        if port.isdigit() and port not in ports:
            ports.append(port)
    return ports


def _find_gopeed_pids() -> set[str]:
    """Return set of PIDs for running gopeed processes."""
    try:
        ps = subprocess.run(
            [
                "powershell", "-NoProfile", "-Command",
                "Get-Process gopeed -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id",
            ],
            capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=10,
        ).stdout
        return {p.strip() for p in ps.split() if p.strip().isdigit()}
    except Exception:
        return set()


def probe(url: str, api_token: str | None = None) -> bool:
    """Quickly verify whether a URL responds as a valid Gopeed API."""
    try:
        import httpx
        headers = {"Content-Type": "application/json"}
        if api_token:
            headers["Authorization"] = f"Bearer {api_token}"
        r = httpx.get(f"{url}/config", timeout=2.0, proxy=None, headers=headers)
        if r.status_code != 200:
            return False
        body = r.json()
        return body.get("code", -1) == 0
    except Exception:
        return False