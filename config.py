"""
配置管理模块

通过环境变量配置 Gopeed MCP Server 的运行参数。

Gopeed 默认每次重启都会随机分配一个本地 API 端口。
如果 Gopeed 配置了固定端口（如 7766），可直接在 URL 中指定端口，跳过自动发现。
当未显式配置具体端口时，本模块支持「自动发现」：通过 netstat 定位
gopeed.exe 实际监听的回环端口，并验证其响应标准 Gopeed API。
"""

import os
import subprocess

# 如果 GOPEED_API_URL 未指定具体端口（只给 host 或无路径），则触发自动发现。
# 显式配置完整 URL（含端口）时优先使用，不做发现。
# 默认配置为 http://127.0.0.1:7766/api/v1（Gopeed 固定端口）。
_AUTO_DISCOVER = os.getenv("GOPEED_API_AUTO_DISCOVER", "1").lower() in ("1", "true", "yes")

# 候选进程名（用于在 netstat 结果中识别 Gopeed 监听端口）
_GOPEED_PROC_NAMES = ("gopeed.exe", "gopeed")


class Settings:
    """运行时配置，从环境变量读取。"""

    def __init__(self) -> None:
        # Gopeed REST API 基础地址（可能由自动发现动态解析）
        raw = os.getenv("GOPEED_API_URL", "").strip()
        if raw:
            # 用户显式配置了 URL：若包含端口则直接使用，否则走自动发现
            self._explicit_url = raw
        else:
            # 未配置：使用默认地址（端口 7766，Gopeed 已配置为固定端口）
            self._explicit_url = "http://127.0.0.1:7766/api/v1"
        # API 令牌（可选，Gopeed 配置了令牌时需要）
        self.api_token: str | None = os.getenv("GOPEED_API_TOKEN") or None
        # HTTP 请求超时（秒）
        self.timeout: float = float(os.getenv("GOPEED_TIMEOUT", "10"))
        # 自动发现缓存
        self._discovered_url: str | None = None
        self._discover_attempted = False

    @property
    def api_url(self) -> str:
        """Gopeed API 地址；必要时自动发现当前端口。"""
        explicit = self._explicit_url
        # 若显式 URL 的 host 部分已含具体端口，则直接使用，不触发发现
        host_part = explicit.split("//", 1)[-1].split("/", 1)[0]
        if ":" in host_part:
            return explicit
        # 否则按需自动发现当前 Gopeed 端口
        return self._discover_url() or explicit

    def reset_discovery_cache(self) -> None:
        """清除端口发现缓存。Gopeed 重启换端口后必须调用此方法才能重新发现。"""
        self._discovered_url = None
        self._discover_attempted = False

    def _discover_url(self) -> str | None:
        """通过 netstat 定位 gopeed 监听端口并验证 API。

        注意：发现失败时（如 MCP server 启动时 Gopeed 尚未监听）不缓存
        None，允许后续请求重新探测，避免一次性失败后永久失效。
        """
        if self._discovered_url is not None:
            return self._discovered_url
        # 不缓存失败结果：每次都实际探测，直到成功定位端口
        ports = self._find_gopeed_ports()
        for port in ports:
            url = f"http://127.0.0.1:{port}/api/v1"
            if self._probe(url):
                self._discovered_url = url
                return url
        return None

    @staticmethod
    def _find_gopeed_ports() -> list[str]:
        """返回 gopeed 进程在 127.0.0.1 上监听的端口列表（有序）。"""
        try:
            out = subprocess.run(
                ["netstat", "-ano"], capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=10
            ).stdout
        except Exception:
            return []
        # 收集 gopeed 进程 PID
        pids: set[str] = set()
        try:
            ps = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-Process gopeed -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id"],
                capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=10,
            ).stdout
            pids = {p.strip() for p in ps.split() if p.strip().isdigit()}
        except Exception:
            pass
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
                continue  # 已知 PID 时按进程过滤
            port = addr.split(":")[-1]
            if port.isdigit() and port not in ports:
                ports.append(port)
        return ports

    def _probe(self, url: str) -> bool:
        """快速验证某 URL 是否为有效的 Gopeed API。"""
        try:
            import httpx
            r = httpx.get(f"{url}/config", timeout=2.0, proxy=None,
                          headers=self.headers if self.api_token else None)
            if r.status_code != 200:
                return False
            body = r.json()
            return body.get("code", -1) == 0
        except Exception:
            return False

    @property
    def headers(self) -> dict[str, str]:
        """构造请求头，包含令牌（如有）。"""
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        return headers

    def __repr__(self) -> str:
        return (
            f"Settings(api_url={self.api_url!r}, "
            f"api_token={'***' if self.api_token else None}, "
            f"timeout={self.timeout})"
        )


# 全局单例
settings = Settings()
