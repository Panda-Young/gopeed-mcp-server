"""
Error types for Gopeed MCP Server.

Provides hierarchical exceptions to distinguish different error scenarios.
"""


class GopeedError(Exception):
    """Base exception for all Gopeed-related errors."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class GopeedConnectionError(GopeedError):
    """Connection failed (refused, timeout, etc)."""
    pass


class GopeedResponseError(GopeedError):
    """HTTP error or non-JSON response from Gopeed."""
    pass


class GopeedApiError(GopeedError):
    """Business logic error returned by Gopeed API (code != 0)."""
    pass