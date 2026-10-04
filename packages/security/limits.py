from dataclasses import dataclass
from time import monotonic

@dataclass
class TokenBucket:
    capacity: int
    refill_per_second: float
    tokens: float = 0
    updated: float = 0

    def __post_init__(self):
        self.tokens = float(self.capacity)
        self.updated = monotonic()

    def allow(self, cost: int = 1) -> bool:
        now = monotonic()
        self.tokens = min(self.capacity, self.tokens + (now - self.updated) * self.refill_per_second)
        self.updated = now
        if self.tokens < cost:
            return False
        self.tokens -= cost
        return True
