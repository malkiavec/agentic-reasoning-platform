from dataclasses import dataclass, field
from typing import Any, Protocol

@dataclass(frozen=True)
class Delegation:
    agent: str
    task: str
    context: dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class AgentResult:
    agent: str
    ok: bool
    output: Any = None
    error: str | None = None

class Subagent(Protocol):
    name: str

    async def run(self, task: str, context: dict[str, Any]) -> Any: ...

class MultiAgentCoordinator:
    """Main-agent delegation boundary with bounded parallel subagent execution."""

    def __init__(self, agents: dict[str, Subagent], max_parallel: int = 4):
        self.agents = dict(agents)
        self.max_parallel = max(1, max_parallel)

    async def execute(self, delegations: list[Delegation]) -> list[AgentResult]:
        import asyncio
        if len(delegations) > 100:
            raise ValueError("delegation_budget_exceeded")
        results: list[AgentResult] = []
        for start in range(0, len(delegations), self.max_parallel):
            batch = delegations[start:start + self.max_parallel]
            async def run_one(item: Delegation) -> AgentResult:
                agent = self.agents.get(item.agent)
                if agent is None:
                    return AgentResult(item.agent, False, error="unknown_subagent")
                try:
                    return AgentResult(item.agent, True, await agent.run(item.task, item.context))
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    return AgentResult(item.agent, False, error=f"subagent_error:{type(exc).__name__}")
            results.extend(await asyncio.gather(*(run_one(item) for item in batch)))
        return results
