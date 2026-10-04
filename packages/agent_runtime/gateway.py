import asyncio
import random

from .models import ModelRequest, ModelResponse
from .providers.base import ModelProvider, ProviderError
from .routing import ModelRouter

class MockProvider(ModelProvider):
    name = "mock"

    async def generate(self, request: ModelRequest) -> ModelResponse:
        if request.response_schema:
            return ModelResponse(
                structured_output={
                    "steps": [{
                        "id": "final",
                        "tool": "__final__",
                        "arguments": {"prompt": request.input[-1].data},
                        "parallel_group": None,
                    }]
                },
                finish_reason="stop",
                provider_request_id="mock-request",
            )
        return ModelResponse(
            output_text="Mock provider response.",
            finish_reason="stop",
            provider_request_id="mock-request",
        )

class ModelGateway:
    def __init__(
        self,
        router: ModelRouter | None = None,
        *,
        max_retries: int = 2,
        base_backoff_seconds: float = 0.25,
        max_backoff_seconds: float = 4.0,
    ):
        self._providers: dict[str, ModelProvider] = {}
        self.router = router
        self.max_retries = max(0, max_retries)
        self.base_backoff_seconds = max(0.0, base_backoff_seconds)
        self.max_backoff_seconds = max(base_backoff_seconds, max_backoff_seconds)

    def register(self, name: str, provider: ModelProvider) -> None:
        if not name or name in self._providers:
            raise ValueError("invalid_or_duplicate_provider")
        self._providers[name] = provider

    def provider(self, name: str) -> ModelProvider:
        if name not in self._providers:
            raise ValueError(f"model provider not configured: {name}")
        return self._providers[name]

    async def generate(self, provider: str, request: ModelRequest) -> ModelResponse:
        return await self.provider(provider).generate(request)

    async def generate_routed(
        self,
        request: ModelRequest,
        *,
        required_capabilities: set[str] | None = None,
        min_context: int = 0,
    ) -> ModelResponse:
        if self.router is None:
            raise ValueError("model_router_not_configured")

        route = self.router.choose(
            required=required_capabilities,
            min_context=min_context,
            reasoning_effort=request.reasoning_effort,
        )
        providers = (route.provider, *route.fallback_providers)
        last: Exception | None = None

        for provider_name in providers:
            if provider_name not in self._providers:
                continue
            provider_route = self.router.route_for(provider_name) or route
            provider_request = request.model_copy(update={"model": provider_route.model})
            for attempt in range(self.max_retries + 1):
                try:
                    return await self.provider(provider_name).generate(provider_request)
                except ProviderError as exc:
                    last = exc
                    if not exc.retryable or attempt >= self.max_retries:
                        break
                    delay = min(
                        self.max_backoff_seconds,
                        self.base_backoff_seconds * (2 ** attempt),
                    )
                    await asyncio.sleep(random.uniform(0.0, delay))
                except ValueError as exc:
                    last = exc
                    break

        raise RuntimeError("all_model_providers_failed") from last
