"""Business handler registry.

Handlers are registered only when their source-backed implementation is installed. Unknown
job types are failed explicitly by the consumer instead of being acknowledged or fabricated.
"""
from __future__ import annotations

from worker.runtime import JobHandler


def build_handler_registry() -> dict[str, JobHandler]:
    return {}
