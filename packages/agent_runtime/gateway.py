from dataclasses import dataclass

from .models import ModelRequest, ModelResponse
from .routing import ModelRouter

class ModelProvider:
    async def generate(self, request: ModelRequest) -> ModelResponse:
        raise NotImplementedError

@dataclass
class MockProvider(ModelProvider):
    name: str = "mock"

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
        return ModelResponse(output_text="Mock provider response.",
                             finish_reason="stop",
                             provider_request_id="mock-request")

class ModelGateway:
    def __init__(self, router: ModelRouter | None = None) -> None:
        self._providers: dict[str, ModelProvider] = {}
        self.router = router

    def register(self, name: str, provider: ModelProvider) -> None:
        self._providers[name] = provider

    def provider(self, name: str) -> ModelProvider:
        try:
            return self._providers[name]
        except KeyError as exc:
            raise ValueError(f"model provider not configured: {name}") from exc

    async def generate(self, provider: str, request: ModelRequest) -> ModelResponse:
        return await self.provider(provider).generate(request)

    async def generate_routed(self, request: ModelRequest, *,
                              required_capabilities: set[str] | None = None,
                              min_context: int = 0) -> ModelResponse:
        if self.router is None:
            raise ValueError("model_router_not_configured")
        route = self.router.choose(required=required_capabilities, min_context=min_context,
                                   reasoning_effort=request.reasoning_effort)
        last_error: Exception | None = None
        for provider_name in (route.provider, *route.fallback_providers):
            try:
                return await self.provider(provider_name).generate(
                    request.model_copy(update={"model": route.model})
                )
            except Exception as exc:
                last_error = exc
        raise RuntimeError("all_model_providers_failed") from last_error
