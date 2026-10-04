from dataclasses import dataclass

@dataclass(frozen=True)
class ModelRoute:
    provider: str
    model: str
    max_context_tokens: int
    capabilities: frozenset[str]
    fallback_providers: tuple[str, ...] = ()

class ModelRouter:
    def __init__(self, routes: list[ModelRoute]):
        self.routes = routes

    def choose(self, *, required: set[str] | None = None,
               min_context: int = 0, reasoning_effort: str | None = None) -> ModelRoute:
        required = required or set()
        candidates = [
            r for r in self.routes
            if r.max_context_tokens >= min_context
            and required <= r.capabilities
            and (reasoning_effort is None
                 or f"reasoning:{reasoning_effort}" in r.capabilities
                 or "reasoning" not in required)
        ]
        if not candidates:
            raise ValueError("no_model_route_matches_requirements")
        return max(candidates, key=lambda r: r.max_context_tokens)
