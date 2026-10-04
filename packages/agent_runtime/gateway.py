from dataclasses import dataclass
from typing import Protocol, Any
from .models import ModelRequest, ModelResponse

class ModelProvider(Protocol):
    async def generate(self, request: ModelRequest) -> ModelResponse: ...

@dataclass
class MockProvider:
    name: str = "mock"

    async def generate(self, request: ModelRequest) -> ModelResponse:
        return ModelResponse(output_text="Mock provider response.", tool_calls=[])

class ModelGateway:
    def __init__(self) -> None:
        self._providers: dict[str, ModelProvider] = {}

    def register(self, name: str, provider: ModelProvider) -> None:
        self._providers[name] = provider

    def provider(self, name: str) -> ModelProvider:
        try:
            return self._providers[name]
        except KeyError as exc:
            raise ValueError(f"model provider not configured: {name}") from exc

    async def generate(self, provider: str, request: ModelRequest) -> ModelResponse:
        return await self.provider(provider).generate(request)
