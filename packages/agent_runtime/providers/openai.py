from .http import HttpModelProvider
from packages.agent_runtime.models import ModelRequest, ModelResponse, ToolCall

class OpenAIProvider(HttpModelProvider):
    def __init__(self, api_key: str, base_url: str="https://api.openai.com/v1", timeout: float=120.0):
        super().__init__(name="openai",base_url=base_url,api_key=api_key,timeout=timeout)
    async def generate(self, request: ModelRequest) -> ModelResponse:
        payload={"model":request.model,"input":[{"role":"user","content":[{"type":p.type,"text":p.data} if p.type=="text" else {"type":p.type,"data":p.data} for p in request.input] }]}
        if request.tools: payload["tools"]=request.tools
        if request.response_schema: payload["text"]={"format":{"type":"json_schema","name":"agent_output","schema":request.response_schema,"strict":True}}
        data=await self.post("/responses",payload)
        calls=[]; text=data.get("output_text","")
        for item in data.get("output",[]):
            if item.get("type") in {"function_call","custom_tool_call"}:
                import json
                args=item.get("arguments",{})
                if isinstance(args,str):
                    try: args=json.loads(args)
                    except ValueError: args={}
                calls.append(ToolCall(id=item.get("call_id",item.get("id","")),name=item.get("name",""),arguments=args))
        structured=None
        if request.response_schema and text:
            import json
            try: structured=json.loads(text)
            except ValueError: pass
        return ModelResponse(output_text=text,tool_calls=calls,structured_output=structured,usage=self.usage(data),finish_reason="stop",provider_request_id=data.get("id"))
