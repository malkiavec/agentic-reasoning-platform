from typing import Any, Protocol
from pydantic import BaseModel

class ContentPart(BaseModel):
    type: str
    data: str
    mime_type: str | None = None

class ModelRequest(BaseModel):
    input: list[ContentPart]
    model: str
    reasoning_effort: str = "medium"
    tools: list[dict[str, Any]] = []

class ModelResponse(BaseModel):
    output_text: str
    tool_calls: list[dict[str, Any]] = []

class ModelProvider(Protocol):
    async def generate(self, request: ModelRequest) -> ModelResponse: ...
