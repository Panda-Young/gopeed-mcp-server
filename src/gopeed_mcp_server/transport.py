"""
Low-level HTTP transport for Gopeed REST API.

Handles: connection, request/response, auto-rediscovery on port change.
"""

from __future__ import annotations

import logging

import httpx

from . import exceptions
from .config import settings

logger = logging.getLogger(__name__)


class GopeedTransport:
    """HTTP transport layer with auto-rediscovery support."""

    def __init__(self, api_url: str | None = None, timeout: float | None = None) -> None:
        self.api_url = (api_url or settings.api_url).rstrip("/")
        self.timeout = timeout or settings.timeout
        self._client = httpx.Client(timeout=self.timeout, proxy=None)
        self._rediscover_on_fail = True

    def request(self, method: str, path: str, **kwargs) -> dict:
        """Send HTTP request and parse Gopeed response.

        Gopeed response format: {"code": 0, "data": ..., "msg": "..."}
        """
        url = f"{self.api_url}{path}"
        headers = kwargs.pop("headers", {})
        headers.update(settings.headers)

        try:
            resp = self._client.request(method, url, headers=headers, **kwargs)
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            # ConnectError / Timeout：Gopeed 可能重启换端口，先清缓存再重发现
            result = self._try_rediscover(method, path, kwargs, headers)
            if result is not None:
                return result
            raise exceptions.GopeedConnectionError(
                f"Cannot connect to Gopeed ({self.api_url}). Please ensure Gopeed is running."
            ) from exc
        except httpx.HTTPError as exc:
            raise exceptions.GopeedConnectionError(f"Request to Gopeed failed: {exc}") from exc

        return self._parse(resp, method, path, kwargs, headers)

    def _try_rediscover(self, method: str, path: str, kwargs: dict, headers: dict) -> dict | None:
        """Attempt to rediscover Gopeed port and retry the request.

        Triggered by:
        - ConnectError / Timeout (in ``request``);
        - HTTP 503 / any response >= 400 (unexpected proxy/middleware replies);
        - 200 but non-JSON body (address hijacked / wrong endpoint).

        Always clears the discovery cache first so the current port is
        re-located after a Gopeed restart.
        """
        if not self._rediscover_on_fail:
            return None
        # 关键：任何重发现触发场景都先清缓存，再重新定位端口
        settings.reset_discovery_cache()
        new_url = settings.api_url.rstrip("/")
        if new_url == self.api_url:
            return None
        logger.info("Rediscovered Gopeed at %s (was %s)", new_url, self.api_url)
        self.api_url = new_url
        self._client.close()
        self._client = httpx.Client(timeout=self.timeout, proxy=None)
        url = f"{self.api_url}{path}"
        try:
            resp = self._client.request(method, url, headers=headers, **kwargs)
        except httpx.HTTPError as exc2:
            raise exceptions.GopeedConnectionError(
                f"Cannot connect to Gopeed ({self.api_url}) after rediscovery."
            ) from exc2
        # 重试得到的响应（即使再次 >= 400）交给 _parse 完整解析。
        # 若重试后仍失败，_parse 会再次调用 _try_rediscover，此时
        # new_url == self.api_url，返回 None 后正常抛出错误，不会死循环。
        return self._parse(resp, method, path, kwargs, headers)

    def _parse(self, resp: httpx.Response, method: str = "", path: str = "",
               kwargs: dict | None = None, headers: dict | None = None) -> dict:
        """Parse Gopeed response, handling rediscovery on HTTP errors.

        Rediscovery triggers (all routed through ``_try_rediscover`` so the
        discovery cache is always reset):
        - HTTP 503 / any response >= 400 (unexpected proxy/middleware replies)
        - 200 but non-JSON body (address hijacked / wrong endpoint)
        """
        kwargs = kwargs or {}
        headers = headers or {}

        # 503 及其它 >= 400 的非预期响应：纳入重发现触发条件
        if self._rediscover_on_fail and resp.status_code >= 400:
            result = self._try_rediscover(method, path, kwargs, headers)
            if result is not None:
                return result

        if resp.status_code >= 400:
            raise exceptions.GopeedResponseError(
                f"Gopeed returned HTTP {resp.status_code}: {resp.text[:200]}",
                status_code=resp.status_code,
            )

        try:
            body = resp.json()
        except ValueError as exc:
            # 200 但非 JSON：属于非预期响应，也尝试一次重发现
            if self._rediscover_on_fail:
                result = self._try_rediscover(method, path, kwargs, headers)
                if result is not None:
                    return result
            raise exceptions.GopeedResponseError(
                f"Gopeed returned non-JSON response: {resp.text[:200]}"
            ) from exc

        if body.get("code", 0) != 0:
            raise exceptions.GopeedApiError(
                f"Gopeed business error: {body.get('msg', 'unknown')} (code={body.get('code')})",
                status_code=body.get("code"),
            )

        return body.get("data", {})

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()
