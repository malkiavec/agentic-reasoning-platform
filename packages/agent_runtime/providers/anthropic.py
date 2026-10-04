from .http import HttpModelProvider
from packages.agent_runtime.models import ModelRequest,ModelResponse,ToolCall
class AnthropicProvider(HttpModelProvider):
    def __init__(self,api_key,base_url="https://api.anthropic.com/v1",timeout=120.0): super().__init__(name="anthropic",base_url=base_url,api_key=api_key,timeout=timeout)
    async def generate(self,request):
        content=[{"type":"text","text":p.data} for p in request.input]
        payload={"model":request.model,"max_tokens":request.max_output_tokens or 4096,"messages":[{"role":"user","content":content}]}
        if request.tools: payload["tools"]=request.tools
        data=await self.post("/messages",payload,{"x-api-key":self.api_key or "","anthropic-version":"2023-06-01"})
        text=""; calls=[]
        for block in data.get("content",[]):
            if block.get("type")=="text": text+=block.get("text","")
            elif block.get("type")=="tool_use": calls.append(ToolCall(id=block.get("id",""),name=block.get("name",""),arguments=block.get("input") or {}))
        return ModelResponse(output_text=text,tool_calls=calls,usage=self.usage(data),finish_reason=data.get("stop_reason"),provider_request_id=data.get("id"))
