import json
from collections.abc import AsyncIterator

import httpx

from .base import ProviderError
from .http import HttpModelProvider
from packages.agent_runtime.models import ContentPart, ModelRequest, ModelResponse, ModelStreamEvent, ToolCall


class OpenAIProvider(HttpModelProvider):
    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1", timeout: float = 120.0):
        super().__init__(name="openai", base_url=base_url, api_key=api_key, timeout=timeout)

    @staticmethod
    def _content(part: ContentPart) -> dict:
        if part.type == "text":
            return {"type": "input_text", "text": part.data}
        if part.type == "image":
            return {"type": "input_image", "image_url": part.data}
        if part.type in {"file", "pdf", "document"}:
            item = {"type": "input_file", "file_data": part.data}
            if part.mime_type:
                item["filename"] = f"input.{part.mime_type.split("/")[-1]}"
            return item
        raise ValueError(f"unsupported_content_type:{part.type}")

    @classmethod
    def _payload(cls, request: ModelRequest, *, stream: bool = False) -> dict:
        payload = {
            "model": request.model,
            "input": [{"role": "user", "content": [cls._content(p) for p in request.input]}],
        }
        if request.tools:
            payload["tools"] = request.tools
        if request.reasoning_effort:
            payload["reasoning"] = {"effort": request.reasoning_effort}
        if request.response_schema:
            payload["text"] = {"format": {
                "type": "json_schema",
                "name": "agent_output",
                "schema": request.response_schema,
                "strict": True,
            }}
        if request.max_output_tokens is not None:
            payload["max_output_tokens"] = request.max_output_tokens
        if stream:
            payload["stream"] = True
        return payload

    async def generate(self, request: ModelRequest) -> ModelResponse:
        data = await self.post("/responses", self._payload(request), {})
        calls = []
        text = data.get("output_text", "")
        for item in data.get("output", []):
            if item.get("type") in {"function_call", "custom_tool_call"}:
                args = item.get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except ValueError:
                        args = {}
                calls.append(ToolCall(
                    id=item.get("call_id", item.get("id", "")),
                    name=item.get("name", ""),
                    arguments=args,
                ))
        structured = None
        if request.response_schema and text:
            try:
                structured = json.loads(text)
            except ValueError:
                pass
        return ModelResponse(
            output_text=text, tool_calls=calls, structured_output=structured,
            usage=self.usage(data), finish_reason="stop",
            provider_request_id=data.get("id"),
        )

    async def stream(self, request: ModelRequest) -> AsyncIterator[ModelStreamEvent]:
        headers = self._headers({"Accept": "text/event-stream"})
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST", self.base_url + "/responses",
                    json=self._payload(request, stream=True), headers=headers
                ) as response:
                    if response.status_code >= 400:
                        body = await response.aread()
                        retryable = response.status_code == 429 or response.status_code >= 500
                        raise ProviderError(
                            f"provider_http_{response.status_code}: {body[:500]!r}",
                            retryable=retryable, status_code=response.status_code
                        )
                    async for line in response.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        payload = line[5:].strip()
                        if payload == "[DONE]":
                            break
                        try:
                            event = json.loads(payload)
                        except ValueError:
                            continue
                        event_type = event.get("type", "")
                        if event_type in {"response.output_text.delta", "response.refusal.delta"}:
                            yield ModelStreamEvent(type="text.delta", text=event.get("delta", ""))
                        elif event_type == "response.completed":
                            response_data = event.get("response") or {}
                            usage = self.usage(response_data)
                            yield ModelStreamEvent(
                                type="response.completed",
                                response=ModelResponse(
                                    output_text=response_data.get("output_text", ""),
                                    usage=usage,
                                    provider_request_id=response_data.get("id"),
                                ),
                                usage=usage,
                            )
        except httpx.TimeoutException as exc:
            raise ProviderError("provider_timeout", retryable=True) from exc
        except httpx.HTTPError as exc:
            raise ProviderError("provider_transport_error", retryable=True) from exc
