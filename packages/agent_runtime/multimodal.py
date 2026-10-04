from dataclasses import dataclass
from typing import Literal

MediaType = Literal["text", "image", "video", "audio", "pdf"]

@dataclass(frozen=True)
class InputAsset:
    type: MediaType
    uri: str
    mime_type: str
    sha256: str | None = None
    metadata: dict[str, str] | None = None

class AssetIngestor:
    """Provider-neutral ingestion contract. Binary processing stays outside the model prompt."""
    async def ingest(self, uri: str, mime_type: str) -> InputAsset:
        kind = "pdf" if mime_type == "application/pdf" else (
            "image" if mime_type.startswith("image/") else
            "video" if mime_type.startswith("video/") else
            "audio" if mime_type.startswith("audio/") else "text"
        )
        return InputAsset(kind, uri, mime_type)
