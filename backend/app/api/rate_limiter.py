import time
from collections import defaultdict


class InMemoryRateLimiter:
    def __init__(self):
        self._attempts = defaultdict(list)

    def check(self, key: str, max_attempts: int = 5, window: int = 60) -> bool:
        now = time.time()
        self._attempts[key] = [t for t in self._attempts[key] if now - t < window]
        if len(self._attempts[key]) >= max_attempts:
            return False
        self._attempts[key].append(now)
        return True


rate_limiter = InMemoryRateLimiter()
