from .http import HttpModelProvider
from packages.agent_runtime.models import ModelRequest, ModelResponse

class OpenAICompatibleProvider(HttpModelProvider):
    def __init__(self, name="local", base_url="http://localhost:11434/v1", api_key=None, timeout=300.0):
        super().__init__(name=name, base_url=base_url, api_key=api_key, timeout=timeout)

    async def generate(self, request: ModelRequest) -> ModelResponse:
        payload={"model":request.model,"messages":[{"role":"user","content":p.data} for p in request.input]}
        if request.tools: payload["tools"]=[{"type":"function","function":t} for t in request.tools]
        data=await self.post("/chat/completions",payload)
        choice=(data.get("choices") or [{}])[0]
        msg=choice.get("message") or {}
        return ModelResponse(output_text=msg.get("content") or "", usage=self.usage(data), finish_reason=choice.get("finish_reason"), provider_request_id=data.get("id"))
