from __future__ import annotations

import time
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.base import Checkpoint


_MAX_THREADS = 100
_THREAD_TTL = 3600


class SizeBoundedCheckpointer(MemorySaver):
    def __init__(self, thread_ttl: int = _THREAD_TTL, max_threads: int = _MAX_THREADS):
        super().__init__()
        self._thread_ttl = thread_ttl
        self._max_threads = max_threads
        self._thread_timestamps: dict[str, float] = {}

    def put(self, config: dict, checkpoint: Checkpoint, metadata: dict, new_versions: dict) -> None:
        thread_id = config["configurable"]["thread_id"]
        self._thread_timestamps[thread_id] = time.monotonic()
        self._evict_stale()
        super().put(config, checkpoint, metadata, new_versions)

    def _evict_stale(self) -> None:
        now = time.monotonic()
        stale = [
            tid for tid, ts in self._thread_timestamps.items()
            if now - ts > self._thread_ttl
        ]
        for tid in stale:
            self.storage.pop(tid, None)
            self._thread_timestamps.pop(tid, None)

        if len(self._thread_timestamps) > self._max_threads:
            sorted_ids = sorted(self._thread_timestamps, key=self._thread_timestamps.get)
            for tid in sorted_ids[: len(sorted_ids) - self._max_threads]:
                self.storage.pop(tid, None)
                self._thread_timestamps.pop(tid, None)