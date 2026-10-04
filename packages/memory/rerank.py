from dataclasses import dataclass

@dataclass(frozen=True)
class RankedHit:
    content: str
    score: float
    source: str

class Reranker:
    async def rerank(self, query: str, hits: list[RankedHit]) -> list[RankedHit]:
        return sorted(hits, key=lambda hit: hit.score, reverse=True)
