from abc import ABC, abstractmethod
from packages.agent_runtime.models import ModelRequest, ModelResponse

class ProviderError(RuntimeError):
    def __init__(self, message: str, *, retryable: bool = False, status_code: int | None = None):
        super().__init__(message); self.retryable = retryable; self.status_code = status_code

class ModelProvider(ABC):
    name: str
    @abstractmethod
    async def generate(self, request: ModelRequest) -> ModelResponse: ...
