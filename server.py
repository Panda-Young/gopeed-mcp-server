"""
Gopeed MCP Server 主入口

通过 stdio 传输与 MCP 客户端（如 VS Code Copilot Chat）通信，
将自然语言请求转化为对 Gopeed 下载管理器的 REST API 调用。

启动方式：python server.py
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from gopeed_client import GopeedClient, GopeedError

# 创建 MCP Server 实例，名称为 gopeed
mcp = FastMCP("gopeed")

# Gopeed API 客户端（延迟初始化，首次调用时创建）
_client: GopeedClient | None = None


def get_client() -> GopeedClient:
    """获取或创建 Gopeed 客户端单例。"""
    global _client
    if _client is None:
        _client = GopeedClient()
    return _client


def handle_error(exc: Exception) -> str:
    """统一异常处理，返回友好的错误信息字符串。"""
    if isinstance(exc, GopeedError):
        return f"❌ {exc}"
    return f"❌ 发生未知错误：{exc}"


# ======================================================================
# MCP Tools
# ======================================================================


@mcp.tool()
def create_download_task(url: str, name: str | None = None, connections: int | None = None) -> str:
    """创建一个新的下载任务。

    Args:
        url: 要下载的文件链接（HTTP/HTTPS/Magnet 等）。
        name: 可选，保存的文件名，不指定则使用默认名称。
        connections: 可选，HTTP 并发连接数，不指定则使用 Gopeed 当前配置。

    Returns:
        任务创建结果，包含任务 ID。
    """
    try:
        result = get_client().create_task(url=url, name=name, connections=connections)
        return f"✅ {result['message']}"
    except Exception as exc:
        return handle_error(exc)


@mcp.tool()
def list_tasks(status: str | None = None) -> str:
    """列出所有下载任务，可按状态过滤。

    Args:
        status: 可选，按状态过滤任务。可选值：
            - ready: 等待中
            - running: 下载中
            - pause: 已暂停
            - done: 已完成
            - error: 出错
            - unknown: 未知

    Returns:
        任务列表，包含每个任务的 ID、名称、状态、速度、进度和大小。
    """
    try:
        tasks = get_client().list_tasks(status=status)
        if not tasks:
            return "📋 当前没有下载任务。"

        lines = [f"📋 共 {len(tasks)} 个任务：\n"]
        for i, t in enumerate(tasks, 1):
            lines.append(
                f"{i}. 【{t['status']}】{t['name']}\n"
                f"   ID: {t['id']}\n"
                f"   进度: {t['progress']}%（{t['downloaded']} / {t['size']}）\n"
                f"   速度: {t['speed']}"
            )
        return "\n".join(lines)
    except Exception as exc:
        return handle_error(exc)


@mcp.tool()
def get_task_detail(task_id: str) -> str:
    """获取指定下载任务的详细信息。

    Args:
        task_id: 任务 ID（可通过 list_tasks 查看）。

    Returns:
        任务的详细信息，包括状态、速度、进度、大小等。
    """
    try:
        t = get_client().get_task_detail(task_id)
        return (
            f"📦 任务详情\n"
            f"名称: {t['name']}\n"
            f"ID: {t['id']}\n"
            f"状态: {t['status']}\n"
            f"进度: {t['progress']}%\n"
            f"已下载: {t['downloaded']} / {t['size']}\n"
            f"当前速度: {t['speed']}"
        )
    except Exception as exc:
        return handle_error(exc)


@mcp.tool()
def pause_task(task_id: str) -> str:
    """暂停指定的下载任务。

    Args:
        task_id: 要暂停的任务 ID。

    Returns:
        暂停操作结果。
    """
    try:
        result = get_client().pause_task(task_id)
        return f"⏸️ {result['message']}"
    except Exception as exc:
        return handle_error(exc)


@mcp.tool()
def resume_task(task_id: str) -> str:
    """恢复（继续）指定的已暂停下载任务。

    Args:
        task_id: 要恢复的任务 ID。

    Returns:
        恢复操作结果。
    """
    try:
        result = get_client().resume_task(task_id)
        return f"▶️ {result['message']}"
    except Exception as exc:
        return handle_error(exc)


@mcp.tool()
def delete_task(task_id: str, force: bool = False) -> str:
    """删除指定的下载任务。

    Args:
        task_id: 要删除的任务 ID。
        force: 是否同时删除已下载的文件，默认为 False（仅删除任务记录）。

    Returns:
        删除操作结果。
    """
    try:
        result = get_client().delete_task(task_id, force=force)
        return f"🗑️ {result['message']}"
    except Exception as exc:
        return handle_error(exc)


@mcp.tool()
def get_config() -> str:
    """获取 Gopeed 当前配置信息。

    Returns:
        当前配置，包括下载目录、并发连接数、User-Agent、代理状态等。
    """
    try:
        cfg = get_client().get_config()
        proxy_status = "已启用" if cfg["proxy_enabled"] else "已禁用"
        return (
            f"⚙️ Gopeed 当前配置\n"
            f"下载目录: {cfg['download_dir']}\n"
            f"并发连接数: {cfg['connections']}\n"
            f"User-Agent: {cfg['user_agent'] or '(默认)'}\n"
            f"代理: {proxy_status}"
            + (f"（{cfg['proxy_url']}）" if cfg["proxy_enabled"] and cfg["proxy_url"] else "")
        )
    except Exception as exc:
        return handle_error(exc)


@mcp.tool()
def update_config(
    connections: int | None = None,
    download_dir: str | None = None,
    proxy_enabled: bool | None = None,
) -> str:
    """更新 Gopeed 配置，只传需要修改的字段即可。

    Args:
        connections: 可选，HTTP 并发连接数（如 16、32）。
        download_dir: 可选，下载目录的完整路径。
        proxy_enabled: 可选，是否启用代理（True/False）。

    Returns:
        更新后的配置信息。
    """
    try:
        cfg = get_client().update_config(
            connections=connections,
            download_dir=download_dir,
            proxy_enabled=proxy_enabled,
        )
        proxy_status = "已启用" if cfg["proxy_enabled"] else "已禁用"
        return (
            f"✅ 配置已更新\n"
            f"下载目录: {cfg['download_dir']}\n"
            f"并发连接数: {cfg['connections']}\n"
            f"代理: {proxy_status}"
        )
    except Exception as exc:
        return handle_error(exc)


# ======================================================================
# 入口
# ======================================================================

if __name__ == "__main__":
    # 通过 stdio 传输启动 MCP Server（VS Code Copilot Chat 默认支持）
    mcp.run(transport="stdio")
