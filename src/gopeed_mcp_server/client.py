"""
Gopeed REST API client.

Provides high-level methods for task and configuration management,
using the transport layer for HTTP communication.
"""

from __future__ import annotations

from . import constants
from .transport import GopeedTransport


class GopeedClient:
    """High-level Gopeed REST API client."""

    def __init__(self, api_url: str | None = None, timeout: float | None = None) -> None:
        self._transport = GopeedTransport(api_url=api_url, timeout=timeout)

    # ------------------------------------------------------------------
    # Task management
    # ------------------------------------------------------------------

    def create_task(self, url: str, name: str | None = None,
                    connections: int | None = None) -> dict:
        """Create a download task."""
        req_body: dict = {"url": url}
        if name:
            req_body["name"] = name
        extra: dict = {}
        if connections is not None:
            extra["http"] = {"connections": connections}
        if extra:
            req_body["extra"] = extra
        data = self._transport.request("POST", "/tasks", json={"req": req_body})
        task_id = data.get("id", "") if isinstance(data, dict) else str(data)
        return {"id": task_id, "message": f"Download task created, ID: {task_id}"}

    def list_tasks(self, status: str | None = None) -> list[dict]:
        """List all tasks, optionally filtered by status."""
        data = self._transport.request("GET", "/tasks")
        tasks = data if isinstance(data, list) else data.get("tasks", [])
        normalized = [_normalize_task(t) for t in tasks]
        if status:
            normalized = [t for t in normalized if t["status"] == status]
        return normalized

    def get_task_detail(self, task_id: str) -> dict:
        """Get detailed info for a single task."""
        data = self._transport.request("GET", f"/tasks/{task_id}")
        return _normalize_task(data)

    def pause_task(self, task_id: str) -> dict:
        """Pause a task."""
        self._transport.request("PUT", f"/tasks/{task_id}/pause")
        return {"id": task_id, "message": f"Task {task_id} paused"}

    def resume_task(self, task_id: str) -> dict:
        """Resume a paused task."""
        self._transport.request("PUT", f"/tasks/{task_id}/continue")
        return {"id": task_id, "message": f"Task {task_id} resumed"}

    def delete_task(self, task_id: str, force: bool = False) -> dict:
        """Delete a task."""
        params = {"force": "true"} if force else None
        self._transport.request("DELETE", f"/tasks/{task_id}", params=params)
        msg = f"Task {task_id} deleted"
        if force:
            msg += " (also removed downloaded files)"
        return {"id": task_id, "message": msg}

    # ------------------------------------------------------------------
    # Configuration management
    # ------------------------------------------------------------------

    def get_config(self) -> dict:
        """Get current Gopeed configuration."""
        data = self._transport.request("GET", "/config")
        protocol_cfg = data.get("protocolConfig", {}) or {}
        http_cfg = protocol_cfg.get("http", {}) or {}
        proxy_cfg = data.get("proxy", {}) or {}

        proxy_url = ""
        if proxy_cfg.get("enable") and proxy_cfg.get("host"):
            scheme = proxy_cfg.get("scheme", "http")
            host = proxy_cfg.get("host", "")
            proxy_url = f"{scheme}://{host}"

        return {
            "download_dir": data.get("downloadDir", ""),
            "connections": http_cfg.get("connections", 0),
            "user_agent": http_cfg.get("userAgent", ""),
            "proxy_enabled": proxy_cfg.get("enable", False),
            "proxy_url": proxy_url,
            "raw": data,
        }

    def update_config(self, connections: int | None = None,
                      download_dir: str | None = None,
                      proxy_enabled: bool | None = None) -> dict:
        """Update Gopeed configuration (only provided fields)."""
        current = self._transport.request("GET", "/config")
        if download_dir is not None:
            current["downloadDir"] = download_dir
        if connections is not None:
            protocol_cfg = current.setdefault("protocolConfig", {})
            http_cfg = protocol_cfg.setdefault("http", {})
            http_cfg["connections"] = connections
        if proxy_enabled is not None:
            proxy_cfg = current.setdefault("proxy", {})
            proxy_cfg["enable"] = proxy_enabled
        self._transport.request("PUT", "/config", json=current)
        return self.get_config()

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._transport.close()


# ------------------------------------------------------------------
# Formatting helpers
# ------------------------------------------------------------------

def _format_speed(bytes_per_sec: int | float | None) -> str:
    if bytes_per_sec is None:
        return "0 B/s"
    if bytes_per_sec >= 1024 * 1024:
        return f"{bytes_per_sec / (1024 * 1024):.2f} MB/s"
    if bytes_per_sec >= 1024:
        return f"{bytes_per_sec / 1024:.2f} KB/s"
    return f"{bytes_per_sec:.0f} B/s"


def _format_size(num_bytes: int | float | None) -> str:
    if num_bytes is None or num_bytes == 0:
        return "0 B"
    value = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024:
            return f"{value:.2f} {unit}"
        value /= 1024
    return f"{value:.2f} PB"


def _calc_progress(downloaded: int | None, size: int | None) -> float:
    if not size or size <= 0 or downloaded is None:
        return 0.0
    return round(downloaded / size * 100, 2)


def _normalize_task(task: dict) -> dict:
    """Convert raw task data to a friendly format."""
    downloaded = task.get("downloaded", 0)
    size = task.get("size", 0)
    speed = task.get("speed", 0)
    return {
        "id": task.get("id", ""),
        "name": task.get("name", ""),
        "status": task.get("status", constants.UNKNOWN),
        "speed": _format_speed(speed),
        "speed_bytes": speed,
        "progress": _calc_progress(downloaded, size),
        "downloaded": _format_size(downloaded),
        "downloaded_bytes": downloaded,
        "size": _format_size(size),
        "size_bytes": size,
    }