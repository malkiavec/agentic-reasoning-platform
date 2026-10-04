import httpx
from .base import ModelProvider, ProviderError
from packages.agent_runtime.models import ModelRequest, ModelResponse, ToolCall, Usage

class HttpModelProvider(ModelProvider):
    def __init__(self, *, name: str, base_url: str, api_key: str | None = None, timeout: float = 120.0):
        self.name=name; self.base_url=base_url.rstrip("/"); self.api_key=api_key; self.timeout=timeout
    async def post(self, path: str, payload: dict, headers: dict[str,str] | None = None) -> dict:
        h={"Content-Type":"application/json", **(headers or {})}
        if self.api_key: h["Authorization"]=f"Bearer {self.api_key}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                r=await client.post(self.base_url+path,json=payload,headers=h)
        except httpx.TimeoutException as e: raise ProviderError("provider_timeout",retryable=True) from e
        except httpx.HTTPError as e: raise ProviderError("provider_transport_error",retryable=True) from e
        if r.status_code >= 400:
            retryable=r.status_code==429 or r.status_code>=500
            raise ProviderError(f"provider_http_{r.status_code}: {r.text[:500]}",retryable=retryable,status_code=r.status_code)
        return r.json()
    @staticmethod
    def usage(data: dict) -> Usage:
        u=data.get("usage") or {}
        return Usage(input_tokens=int(u.get("input_tokens",u.get("prompt_tokens",0)) or 0),output_tokens=int(u.get("output_tokens",u.get("completion_tokens",0)) or 0),total_tokens=int(u.get("total_tokens",0) or 0))
