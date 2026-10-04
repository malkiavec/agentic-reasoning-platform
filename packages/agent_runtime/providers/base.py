from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from packages.agent_runtime.models import ModelRequest, ModelResponse, ModelStreamEvent

class ProviderError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        retryable: bool = False,
        status_code: int | None = None,
    ):
        super().__init__(message)
        self.retryable = retryable
        self.status_code = status_code

class ModelProvider(ABC):
    name: str

    @abstractmethod
    async def generate(self, request: ModelRequest) -> ModelResponse:
        ...

    async def stream(self, request: ModelRequest) -> AsyncIterator[ModelStreamEvent]:
        response = await self.generate(request)
        if response.output_text:
            yield ModelStreamEvent(type="text.delta", text=response.output_text)
        yield ModelStreamEvent(type="response.completed", response=response, usage=response.usage)
