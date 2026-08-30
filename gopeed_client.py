"""
Gopeed REST API 客户端封装

提供对 Gopeed 下载管理器任务管理和配置管理接口的调用。
所有方法均返回结构化字典，便于 MCP Tool 直接返回给客户端。
"""

from __future__ import annotations

import httpx

from config import settings


class GopeedError(Exception):
    """Gopeed API 调用异常。"""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class GopeedClient:
    """Gopeed REST API 客户端。"""

    def __init__(self, api_url: str | None = None, timeout: float | None = None) -> None:
        self.api_url = (api_url or settings.api_url).rstrip("/")
        self.timeout = timeout or settings.timeout
        # 关键：禁用代理。Gopeed 监听本地回环，若 httpx 沿用系统代理
        # （Gopeed 自身 proxy.enable=true 时），localhost 请求会被代理拦截
        # 返回 503，导致所有工具调用失败。本地管理接口无需走代理。
        self._client = httpx.Client(timeout=self.timeout, proxy=None)
        # Gopeed 重启会随机更换端口：任何连接失败或非预期响应都尝试自动重发现。
        # 无论是否显式配置端口，均启用重发现（显式端口失效时回退到自动发现）。
        self._rediscover_on_fail = True

    # ------------------------------------------------------------------
    # 内部工具方法
    # ------------------------------------------------------------------

    def _request(self, method: str, path: str, **kwargs) -> dict:
        """发送 HTTP 请求并解析 Gopeed 统一响应格式。

        Gopeed 响应格式: {"code": 0, "data": ..., "msg": "..."}
        code != 0 表示业务错误。
        """
        url = f"{self.api_url}{path}"
        headers = kwargs.pop("headers", {})
        headers.update(settings.headers)

        try:
            resp = self._client.request(method, url, headers=headers, **kwargs)
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            # Gopeed 重启后端口会变：连接拒绝或超时都先清缓存再自动重发现一次
            if self._rediscover_on_fail:
                settings.reset_discovery_cache()
                new_url = settings.api_url  # 重新解析，触发发现
                if new_url.rstrip("/") != self.api_url:
                    self.api_url = new_url.rstrip("/")
                    self._client.close()
                    self._client = httpx.Client(timeout=self.timeout, proxy=None)
                    url = f"{self.api_url}{path}"
                    try:
                        resp = self._client.request(method, url, headers=headers, **kwargs)
                    except httpx.HTTPError as exc2:
                        raise GopeedError(
                            f"无法连接到 Gopeed（{self.api_url}），自动重发现端口后仍失败。"
                        ) from exc2
                    else:
                        return self._parse(resp)
            raise GopeedError(
                f"无法连接到 Gopeed（{self.api_url}），请确认 Gopeed 已启动且端口正确。"
            ) from exc
        except httpx.HTTPError as exc:
            raise GopeedError(f"请求 Gopeed 失败：{exc}") from exc

        return self._parse(resp, method=method, path=path, headers=headers, **kwargs)

    def _parse(self, resp, method: str = "", path: str = "", **kwargs) -> dict:
        """解析 Gopeed 统一响应格式。

        Gopeed 响应格式: {"code": 0, "data": ..., "msg": "..."}
        code != 0 表示业务错误。
        """
        # 端口失效但被代理/中间层返回 503 等非预期响应时，先清缓存再自动重发现一次
        if self._rediscover_on_fail and resp.status_code >= 400:
            settings.reset_discovery_cache()
            new_url = settings.api_url
            if new_url.rstrip("/") != self.api_url:
                self.api_url = new_url.rstrip("/")
                self._client.close()
                self._client = httpx.Client(timeout=self.timeout, proxy=None)
                if method:
                    try:
                        resp = self._client.request(method, f"{self.api_url}{path}", **kwargs)
                    except httpx.HTTPError:
                        pass
                    else:
                        return self._parse(resp)
        if resp.status_code >= 400:
            raise GopeedError(
                f"Gopeed 返回 HTTP {resp.status_code}：{resp.text[:200]}",
                status_code=resp.status_code,
            )

        try:
            body = resp.json()
        except ValueError as exc:
            raise GopeedError(f"Gopeed 返回了非 JSON 响应：{resp.text[:200]}") from exc

        if body.get("code", 0) != 0:
            raise GopeedError(
                f"Gopeed 业务错误：{body.get('msg', '未知错误')}（code={body.get('code')}）"
            )

        return body.get("data", {})

    @staticmethod
    def _format_speed(bytes_per_sec: int | float | None) -> str:
        """将字节/秒转换为人类可读的速度字符串。"""
        if bytes_per_sec is None:
            return "0 B/s"
        if bytes_per_sec >= 1024 * 1024:
            return f"{bytes_per_sec / (1024 * 1024):.2f} MB/s"
        if bytes_per_sec >= 1024:
            return f"{bytes_per_sec / 1024:.2f} KB/s"
        return f"{bytes_per_sec:.0f} B/s"

    @staticmethod
    def _format_size(num_bytes: int | float | None) -> str:
        """将字节数转换为人类可读的大小字符串。"""
        if num_bytes is None or num_bytes == 0:
            return "0 B"
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if num_bytes < 1024:
                return f"{num_bytes:.2f} {unit}"
            num_bytes /= 1024
        return f"{num_bytes:.2f} PB"

    @staticmethod
    def _calc_progress(downloaded: int | None, size: int | None) -> float:
        """计算下载进度百分比。"""
        if not size or size <= 0 or downloaded is None:
            return 0.0
        return round(downloaded / size * 100, 2)

    def _normalize_task(self, task: dict) -> dict:
        """将原始任务数据转换为友好格式。"""
        downloaded = task.get("downloaded", 0)
        size = task.get("size", 0)
        speed = task.get("speed", 0)
        return {
            "id": task.get("id", ""),
            "name": task.get("name", ""),
            "status": task.get("status", "unknown"),
            "speed": self._format_speed(speed),
            "speed_bytes": speed,
            "progress": self._calc_progress(downloaded, size),
            "downloaded": self._format_size(downloaded),
            "downloaded_bytes": downloaded,
            "size": self._format_size(size),
            "size_bytes": size,
        }

    # ------------------------------------------------------------------
    # 任务管理
    # ------------------------------------------------------------------

    def create_task(
        self,
        url: str,
        name: str | None = None,
        connections: int | None = None,
    ) -> dict:
        """创建下载任务。

        Args:
            url: 下载链接。
            name: 可选文件名，不指定则使用服务器返回的名称。
            connections: HTTP 并发连接数，不指定则使用 Gopeed 当前配置。

        Returns:
            包含任务 ID 的字典。
        """
        req_body: dict = {"url": url}
        if name:
            req_body["name"] = name

        extra: dict = {}
        if connections is not None:
            extra["http"] = {"connections": connections}
        if extra:
            req_body["extra"] = extra

        data = self._request("POST", "/tasks", json={"req": req_body})
        task_id = data.get("id", "") if isinstance(data, dict) else str(data)
        return {"id": task_id, "message": f"下载任务已创建，任务 ID：{task_id}"}

    def list_tasks(self, status: str | None = None) -> list[dict]:
        """列出所有下载任务。

        Args:
            status: 可选状态过滤（ready / running / pause / done / error / unknown）。

        Returns:
            任务列表，每个任务包含 ID、名称、状态、速度、进度等信息。
        """
        data = self._request("GET", "/tasks")
        tasks = data if isinstance(data, list) else data.get("tasks", [])

        normalized = [self._normalize_task(t) for t in tasks]

        if status:
            normalized = [t for t in normalized if t["status"] == status]

        return normalized

    def get_task_detail(self, task_id: str) -> dict:
        """获取单个任务的详细信息。

        Args:
            task_id: 任务 ID。

        Returns:
            任务详细信息。
        """
        data = self._request("GET", f"/tasks/{task_id}")
        return self._normalize_task(data)

    def pause_task(self, task_id: str) -> dict:
        """暂停指定任务。

        Args:
            task_id: 任务 ID。

        Returns:
            操作结果。
        """
        self._request("POST", f"/tasks/{task_id}/pause")
        return {"id": task_id, "message": f"任务 {task_id} 已暂停"}

    def resume_task(self, task_id: str) -> dict:
        """恢复指定任务。

        Args:
            task_id: 任务 ID。

        Returns:
            操作结果。
        """
        self._request("POST", f"/tasks/{task_id}/resume")
        return {"id": task_id, "message": f"任务 {task_id} 已恢复"}

    def delete_task(self, task_id: str, force: bool = False) -> dict:
        """删除任务。

        Args:
            task_id: 任务 ID。
            force: 是否同时删除已下载的文件。

        Returns:
            操作结果。
        """
        params = {"force": "true"} if force else None
        self._request("DELETE", f"/tasks/{task_id}", params=params)
        msg = f"任务 {task_id} 已删除"
        if force:
            msg += "（同时删除了已下载文件）"
        return {"id": task_id, "message": msg}

    # ------------------------------------------------------------------
    # 配置管理
    # ------------------------------------------------------------------

    def get_config(self) -> dict:
        """获取 Gopeed 当前配置。

        Returns:
            包含关键配置项的友好格式字典。
        """
        data = self._request("GET", "/config")

        # Gopeed 配置结构：HTTP 配置在 protocolConfig.http 下，代理在 proxy 下
        protocol_cfg = data.get("protocolConfig", {}) or {}
        http_cfg = protocol_cfg.get("http", {}) or {}
        proxy_cfg = data.get("proxy", {}) or {}

        # 构造代理地址字符串
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

    def update_config(
        self,
        connections: int | None = None,
        download_dir: str | None = None,
        proxy_enabled: bool | None = None,
    ) -> dict:
        """更新 Gopeed 配置（只传需要修改的字段）。

        策略：先 GET 获取完整配置，在其基础上修改指定字段，再 PUT 回去。

        Args:
            connections: HTTP 并发连接数。
            download_dir: 下载目录路径。
            proxy_enabled: 是否启用代理。

        Returns:
            更新后的配置。
        """
        # 先获取当前完整配置
        current = self._request("GET", "/config")

        # 修改指定字段
        if download_dir is not None:
            current["downloadDir"] = download_dir

        # HTTP 并发连接数在 protocolConfig.http.connections
        if connections is not None:
            protocol_cfg = current.setdefault("protocolConfig", {})
            http_cfg = protocol_cfg.setdefault("http", {})
            http_cfg["connections"] = connections

        # 代理开关在 proxy.enable
        if proxy_enabled is not None:
            proxy_cfg = current.setdefault("proxy", {})
            proxy_cfg["enable"] = proxy_enabled

        # PUT 完整配置
        self._request("PUT", "/config", json=current)

        return self.get_config()

    def close(self) -> None:
        """关闭底层 HTTP 客户端。"""
        self._client.close()
