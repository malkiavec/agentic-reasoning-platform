from .http import HttpModelProvider
from packages.agent_runtime.models import ModelRequest, ModelResponse, ToolCall


class AnthropicProvider(HttpModelProvider):
    def __init__(self, api_key, base_url="https://api.anthropic.com/v1", timeout=120.0):
        super().__init__(name="anthropic", base_url=base_url, api_key=api_key, timeout=timeout)

    @staticmethod
    def _content(part):
        if part.type == "text":
            return {"type": "text", "text": part.data}
        if part.type == "image":
            if part.data.startswith("data:") and "," in part.data:
                mime, encoded = part.data[5:].split(",", 1)
                return {"type": "image", "source": {"type": "base64", "media_type": mime.split(";")[0], "data": encoded}}
            return {"type": "image", "source": {"type": "url", "url": part.data}}
        if part.type in {"pdf", "document", "file"}:
            if part.data.startswith("data:") and "," in part.data:
                mime, encoded = part.data[5:].split(",", 1)
                return {"type": "document", "source": {"type": "base64", "media_type": mime.split(";")[0], "data": encoded}}
            return {"type": "document", "source": {"type": "url", "url": part.data}}
        raise ValueError(f"unsupported_content_type:{part.type}")

    async def generate(self, request):
        content = [self._content(p) for p in request.input]
        payload = {
            "model": request.model,
            "max_tokens": request.max_output_tokens or 4096,
            "messages": [{"role": "user", "content": content}],
        }
        if request.tools:
            payload["tools"] = request.tools
        if request.response_schema:
            payload["output_config"] = {"format": {
                "type": "json_schema",
                "schema": request.response_schema,
            }}
        if request.reasoning_effort.lower() in {"low", "medium", "high"}:
            payload["thinking"] = {"type": "adaptive"}
            payload["thinking"]["budget_tokens"] = {"low": 2048, "medium": 8192, "high": 16384}[request.reasoning_effort.lower()]

        data = await self.post("/messages", payload, {"x-api-key": self.api_key or "", "anthropic-version": "2023-06-01"})
        text = ""
        calls = []
        for block in data.get("content", []):
            if block.get("type") == "text":
                text += block.get("text", "")
            elif block.get("type") == "tool_use":
                calls.append(ToolCall(id=block.get("id", ""), name=block.get("name", ""), arguments=block.get("input") or {}))
        return ModelResponse(
            output_text=text,
            tool_calls=calls,
            usage=self.usage(data),
            finish_reason=data.get("stop_reason"),
            provider_request_id=data.get("id"),
        )
