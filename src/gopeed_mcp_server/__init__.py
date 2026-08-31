"""
Gopeed MCP Server — package root.

Re-exports the public API for downstream consumers.
"""

from .client import GopeedClient
from .exceptions import GopeedApiError, GopeedConnectionError, GopeedError, GopeedResponseError

__all__ = [
    "GopeedClient",
    "GopeedError",
    "GopeedConnectionError",
    "GopeedResponseError",
    "GopeedApiError",
]
