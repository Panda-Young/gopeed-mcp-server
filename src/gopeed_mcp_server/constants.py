"""
Task status constants.

Gopeed uses these string status values in the API response.
"""

from typing import Literal

# Status value constants
Status = Literal["ready", "running", "pause", "done", "error", "unknown"]

READY = "ready"
RUNNING = "running"
PAUSE = "pause"
DONE = "done"
ERROR = "error"
UNKNOWN = "unknown"

ALL_STATUSES = (READY, RUNNING, PAUSE, DONE, ERROR, UNKNOWN)
