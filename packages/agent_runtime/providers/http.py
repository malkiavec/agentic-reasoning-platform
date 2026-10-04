import httpx

from .base import ModelProvider, ProviderError
from packages.agent_runtime.models import ModelRequest, ModelResponse, Usage

class HttpModelProvider(ModelProvider):
    def __init__(
        self,
        *,
        name: str,
        base_url: str,
        api_key: str | None = None,
        timeout: float = 120.0,
    ):
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def _headers(self, headers: dict[str, str] | None = None) -> dict[str, str]:
        result = {"Content-Type": "application/json", **(headers or {})}
        if self.api_key:
            result.setdefault("Authorization", f"Bearer {self.api_key}")
        return result

    async def post(
        self,
        path: str,
        payload: dict,
        headers: dict[str, str] | None = None,
    ) -> dict:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.base_url + path,
                    json=payload,
                    headers=self._headers(headers),
                )
        except httpx.TimeoutException as exc:
            raise ProviderError("provider_timeout", retryable=True) from exc
        except httpx.HTTPError as exc:
            raise ProviderError("provider_transport_error", retryable=True) from exc
        if response.status_code >= 400:
            retryable = response.status_code == 429 or response.status_code >= 500
            raise ProviderError(
                f"provider_http_{response.status_code}: {response.text[:500]}",
                retryable=retryable,
                status_code=response.status_code,
            )
        return response.json()

    @staticmethod
    def usage(data: dict) -> Usage:
        usage = data.get("usage") or {}
        return Usage(
            input_tokens=int(usage.get("input_tokens", usage.get("prompt_tokens", 0)) or 0),
            output_tokens=int(
                usage.get("output_tokens", usage.get("completion_tokens", 0)) or 0
            ),
            total_tokens=int(usage.get("total_tokens", 0) or 0),
        )
