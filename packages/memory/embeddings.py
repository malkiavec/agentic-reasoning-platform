import os

import httpx

class EmbeddingError(RuntimeError):
    pass

class EmbeddingProvider:
    async def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI embeddings adapter; output dimensionality must match pgvector schema."""

    def __init__(self, api_key: str | None = None, model: str | None = None,
                 base_url: str = "https://api.openai.com/v1", timeout: float = 60.0):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = model or os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if not self.api_key:
            raise EmbeddingError("embedding_api_key_not_configured")
        if any(not isinstance(text, str) or not text.strip() for text in texts):
            raise EmbeddingError("invalid_embedding_input")
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/embeddings",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={"model": self.model, "input": texts},
                )
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPError as exc:
            raise EmbeddingError("embedding_provider_unavailable") from exc
        data = sorted(payload.get("data", []), key=lambda item: item.get("index", 0))
        vectors = [item.get("embedding") for item in data]
        if len(vectors) != len(texts) or any(not isinstance(v, list) for v in vectors):
            raise EmbeddingError("invalid_embedding_response")
        return vectors
