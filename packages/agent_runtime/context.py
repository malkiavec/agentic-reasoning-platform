from dataclasses import dataclass, field
from typing import Any

@dataclass
class ContextWindow:
    max_tokens: int = 1_000_000
    reserved_output_tokens: int = 16_000
    items: list[Any] = field(default_factory=list)

    @property
    def input_budget(self) -> int:
        return max(0, self.max_tokens - self.reserved_output_tokens)

    def add(self, item: Any) -> None:
        self.items.append(item)

class ContextManager:
    """Long-context policy surface; tokenization and provider-specific limits live in adapters."""
    def __init__(self, window: ContextWindow | None = None):
        self.window = window or ContextWindow()

    def fit(self, items: list[Any], estimated_tokens: list[int]) -> list[Any]:
        total = 0
        selected = []
        for item, cost in zip(items, estimated_tokens):
            if total + cost > self.window.input_budget:
                break
            selected.append(item)
            total += cost
        return selected
