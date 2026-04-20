"""Runtime configuration loaded from the environment.

All config is optional; defaults are safe for local demos.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    host: str
    port: int
    greeting: str

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            host=os.environ.get("HELLO_SERVICE_HOST", "127.0.0.1"),
            port=int(os.environ.get("HELLO_SERVICE_PORT", "8080")),
            greeting=os.environ.get("HELLO_SERVICE_GREETING", "Hello"),
        )
