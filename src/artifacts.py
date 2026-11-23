"""Minimal artifact-reference contract for Phase 1.

Only an in-memory store is implemented. Persistence to a run bundle is
deferred to Phase 4 (Recorder). The interface exists now so events can carry
stable references instead of duplicating large payloads.
"""

from typing import Any
from uuid import uuid4


class ArtifactStore:
    def __init__(self, run_id: str):
        self.run_id = run_id
        self._items: dict[str, Any] = {}

    def save(self, payload: Any, label: str = "artifact") -> str:
        ref = f"{self.run_id}:{label}:{uuid4().hex[:12]}"
        self._items[ref] = payload
        return ref

    def get(self, ref: str) -> Any:
        return self._items[ref]

    def __contains__(self, ref: str) -> bool:
        return ref in self._items
