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

    def route_for(self, provider: str) -> ModelRoute | None:
        return next((route for route in self.routes if route.provider == provider), None)

    def choose(
        self,
        *,
        required: set[str] | None = None,
        min_context: int = 0,
        reasoning_effort: str | None = None,
    ) -> ModelRoute:
        required = required or set()
        candidates = [
            route
            for route in self.routes
            if route.max_context_tokens >= min_context
            and required <= route.capabilities
            and (
                reasoning_effort is None
                or f"reasoning:{reasoning_effort}" in route.capabilities
                or "reasoning" not in required
            )
        ]
        if not candidates:
            raise ValueError("no_model_route_matches_requirements")
        return max(candidates, key=lambda route: route.max_context_tokens)
