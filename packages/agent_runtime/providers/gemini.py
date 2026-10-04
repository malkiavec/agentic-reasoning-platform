from .http import HttpModelProvider
from packages.agent_runtime.models import ModelRequest,ModelResponse,ToolCall
class GeminiProvider(HttpModelProvider):
    def __init__(self,api_key,base_url="https://generativelanguage.googleapis.com/v1beta",timeout=120.0): super().__init__(name="gemini",base_url=base_url,api_key=api_key,timeout=timeout)
    async def generate(self,request):
        payload={"contents":[{"role":"user","parts":[{"text":p.data} for p in request.input]}]}
        if request.tools: payload["tools"]=[{"function_declarations":request.tools}]
        if request.response_schema: payload["generationConfig"]={"responseMimeType":"application/json","responseSchema":request.response_schema}
        data=await self.post(f"/models/{request.model}:generateContent",payload,{"x-goog-api-key":self.api_key or ""})
        candidate=(data.get("candidates") or [{}])[0]; text=""; calls=[]
        for part in (candidate.get("content") or {}).get("parts",[]):
            if "text" in part: text+=part["text"]
            if "functionCall" in part:
                fc=part["functionCall"]; calls.append(ToolCall(id=fc.get("name",""),name=fc.get("name",""),arguments=fc.get("args") or {}))
        import json; structured=None
        if request.response_schema and text:
            try: structured=json.loads(text)
            except ValueError: pass
        return ModelResponse(output_text=text,tool_calls=calls,structured_output=structured,usage=self.usage(data),finish_reason=candidate.get("finishReason"),provider_request_id=data.get("responseId"))
