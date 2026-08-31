"""
Configuration management.

Loads settings from environment variables with sensible defaults.
Supports fixed port (default: 7766) and auto-discovery fallback.
"""

from __future__ import annotations

import os

from . import discovery

_DEFAULT_URL = "http://127.0.0.1:7766/api/v1"


class Settings:
    """Runtime configuration, loaded from environment variables."""

    def __init__(self) -> None:
        raw = os.getenv("GOPEED_API_URL", "").strip()
        self._explicit_url = raw or _DEFAULT_URL
        self.api_token: str | None = os.getenv("GOPEED_API_TOKEN") or None
        self.timeout: float = float(os.getenv("GOPEED_TIMEOUT", "10"))
        self._discovered_url: str | None = None

    @property
    def api_url(self) -> str:
        """Gopeed API base URL; auto-discovers port if not specified in URL."""
        explicit = self._explicit_url
        host_part = explicit.split("//", 1)[-1].split("/", 1)[0]
        if ":" in host_part:
            return explicit
        return self._discover_url() or explicit

    def reset_discovery_cache(self) -> None:
        """Clear discovery cache. Must be called after Gopeed restarts and changes port."""
        self._discovered_url = None

    def _discover_url(self) -> str | None:
        """Discover Gopeed port via netstat and probe."""
        if self._discovered_url is not None:
            return self._discovered_url
        ports = discovery.find_gopeed_ports()
        for port in ports:
            url = f"http://127.0.0.1:{port}/api/v1"
            if discovery.probe(url, self.api_token):
                self._discovered_url = url
                return url
        return None

    @property
    def headers(self) -> dict[str, str]:
        """Request headers with optional API token."""
        hdrs: dict[str, str] = {"Content-Type": "application/json"}
        if self.api_token:
            hdrs["Authorization"] = f"Bearer {self.api_token}"
        return hdrs

    def __repr__(self) -> str:
        return (
            f"Settings(api_url={self.api_url!r}, "
            f"api_token={'***' if self.api_token else None}, "
            f"timeout={self.timeout})"
        )


settings = Settings()