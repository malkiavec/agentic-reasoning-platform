import json

from .http import HttpModelProvider
from packages.agent_runtime.models import ModelRequest, ModelResponse, ToolCall


class GeminiProvider(HttpModelProvider):
    def __init__(self, api_key, base_url="https://generativelanguage.googleapis.com/v1beta", timeout=120.0):
        super().__init__(name="gemini", base_url=base_url, api_key=api_key, timeout=timeout)

    @staticmethod
    def _part(part):
        if part.type == "text":
            return {"text": part.data}
        if part.type == "image":
            if part.data.startswith("data:") and "," in part.data:
                mime, encoded = part.data[5:].split(",", 1)
                return {"inline_data": {"mime_type": mime.split(";")[0], "data": encoded}}
            return {"file_data": {"mime_type": part.mime_type or "image/*", "file_uri": part.data}}
        if part.type in {"file", "pdf", "document", "video"}:
            if part.data.startswith("data:") and "," in part.data:
                mime, encoded = part.data[5:].split(",", 1)
                return {"inline_data": {"mime_type": mime.split(";")[0], "data": encoded}}
            return {"file_data": {"mime_type": part.mime_type or "application/octet-stream", "file_uri": part.data}}
        raise ValueError(f"unsupported_content_type:{part.type}")

    async def generate(self, request: ModelRequest):
        generation_config = {}
        if request.response_schema:
            generation_config.update({
                "responseMimeType": "application/json",
                "responseSchema": request.response_schema,
            })
        if request.max_output_tokens is not None:
            generation_config["maxOutputTokens"] = request.max_output_tokens

        thinking = request.reasoning_effort.lower()
        if thinking in {"minimal", "low", "medium", "high"}:
            generation_config["thinkingConfig"] = {"thinkingLevel": thinking}

        payload = {
            "contents": [{"role": "user", "parts": [self._part(p) for p in request.input]}],
        }
        if request.tools:
            payload["tools"] = [{"function_declarations": request.tools}]
        if generation_config:
            payload["generationConfig"] = generation_config

        data = await self.post(f"/models/{request.model}:generateContent", payload, {"x-goog-api-key": self.api_key or ""})
        candidate = (data.get("candidates") or [{}])[0]
        text = ""
        calls = []
        for part in (candidate.get("content") or {}).get("parts", []):
            if "text" in part:
                text += part["text"]
            if "functionCall" in part:
                fc = part["functionCall"]
                calls.append(ToolCall(id=fc.get("name", ""), name=fc.get("name", ""), arguments=fc.get("args") or {}))
        structured = None
        if request.response_schema and text:
            try:
                structured = json.loads(text)
            except ValueError:
                pass
        return ModelResponse(
            output_text=text,
            tool_calls=calls,
            structured_output=structured,
            usage=self.usage(data),
            finish_reason=candidate.get("finishReason"),
            provider_request_id=data.get("responseId"),
        )
