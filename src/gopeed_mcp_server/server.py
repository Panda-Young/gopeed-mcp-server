"""
Gopeed MCP Server — main entry point.

Communicates with MCP clients (e.g. VS Code Copilot Chat) via stdio transport,
translating natural language requests into Gopeed REST API calls.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from gopeed_mcp_server import GopeedClient, GopeedError

mcp = FastMCP("gopeed")

_client: GopeedClient | None = None


def get_client() -> GopeedClient:
    """Get or create the Gopeed client singleton."""
    global _client
    if _client is None:
        _client = GopeedClient()
    return _client


def handle_error(exc: Exception) -> str:
    """Unified error handling, returning a user-friendly message."""
    if isinstance(exc, GopeedError):
        return f"❌ {exc}"
    return f"❌ Unknown error: {exc}"


# ======================================================================
# MCP Tools
# ======================================================================


@mcp.tool()
def create_download_task(url: str, name: str | None = None, connections: int | None = None) -> str:
    """Create a new download task.

    Args:
        url: Download URL (HTTP/HTTPS/Magnet etc).
        name: Optional save filename.
        connections: Optional HTTP concurrent connections count.
    """
    try:
        result = get_client().create_task(url=url, name=name, connections=connections)
        return f"✅ {result['message']}"
    except Exception as exc:
        return handle_error(exc)


@mcp.tool()
def list_tasks(status: str | None = None) -> str:
    """List all download tasks, optionally filtered by status.

    Args:
        status: Filter by status — ready, running, pause, done, error, unknown.
    """
    try:
        tasks = get_client().list_tasks(status=status)
        if not tasks:
            return "📋 No download tasks."

        lines = [f"📋 {len(tasks)} task(s):\n"]
        for i, t in enumerate(tasks, 1):
            lines.append(
                f"{i}. [{t['status']}] {t['name']}\n"
                f"   ID: {t['id']}\n"
                f"   Progress: {t['progress']}% ({t['downloaded']} / {t['size']})\n"
                f"   Speed: {t['speed']}"
            )
        return "\n".join(lines)
    except Exception as exc:
        return handle_error(exc)


@mcp.tool()
def get_task_detail(task_id: str) -> str:
    """Get detailed info for a specific task.

    Args:
        task_id: Task ID (from list_tasks).
    """
    try:
        t = get_client().get_task_detail(task_id)
        return (
            f"📦 Task Detail\n"
            f"Name: {t['name']}\n"
            f"ID: {t['id']}\n"
            f"Status: {t['status']}\n"
            f"Progress: {t['progress']}%\n"
            f"Downloaded: {t['downloaded']} / {t['size']}\n"
            f"Speed: {t['speed']}"
        )
    except Exception as exc:
        return handle_error(exc)


@mcp.tool()
def pause_task(task_id: str) -> str:
    """Pause a download task.

    Args:
        task_id: Task ID to pause.
    """
    try:
        result = get_client().pause_task(task_id)
        return f"⏸️ {result['message']}"
    except Exception as exc:
        return handle_error(exc)


@mcp.tool()
def resume_task(task_id: str) -> str:
    """Resume a paused download task.

    Args:
        task_id: Task ID to resume.
    """
    try:
        result = get_client().resume_task(task_id)
        return f"▶️ {result['message']}"
    except Exception as exc:
        return handle_error(exc)


@mcp.tool()
def delete_task(task_id: str, force: bool = False) -> str:
    """Delete a download task.

    Args:
        task_id: Task ID to delete.
        force: Also delete downloaded files (default: False).
    """
    try:
        result = get_client().delete_task(task_id, force=force)
        return f"🗑️ {result['message']}"
    except Exception as exc:
        return handle_error(exc)


@mcp.tool()
def get_config() -> str:
    """Get current Gopeed configuration."""
    try:
        cfg = get_client().get_config()
        proxy_status = "Enabled" if cfg["proxy_enabled"] else "Disabled"
        proxy_part = f" ({cfg['proxy_url']})" if cfg["proxy_enabled"] and cfg["proxy_url"] else ""
        return (
            f"⚙️ Gopeed Configuration\n"
            f"Download dir: {cfg['download_dir']}\n"
            f"Connections: {cfg['connections']}\n"
            f"User-Agent: {cfg['user_agent'] or '(default)'}\n"
            f"Proxy: {proxy_status}{proxy_part}"
        )
    except Exception as exc:
        return handle_error(exc)


@mcp.tool()
def update_config(
    connections: int | None = None,
    download_dir: str | None = None,
    proxy_enabled: bool | None = None,
) -> str:
    """Update Gopeed configuration (only provide fields to change).

    Args:
        connections: HTTP concurrent connections (e.g. 16, 32).
        download_dir: Full path to download directory.
        proxy_enabled: Whether to enable proxy (True/False).
    """
    try:
        cfg = get_client().update_config(
            connections=connections,
            download_dir=download_dir,
            proxy_enabled=proxy_enabled,
        )
        proxy_status = "Enabled" if cfg["proxy_enabled"] else "Disabled"
        return (
            f"✅ Configuration updated\n"
            f"Download dir: {cfg['download_dir']}\n"
            f"Connections: {cfg['connections']}\n"
            f"Proxy: {proxy_status}"
        )
    except Exception as exc:
        return handle_error(exc)


# ======================================================================
# Entry point
# ======================================================================

def main() -> None:
    """Run the MCP server via stdio transport."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()