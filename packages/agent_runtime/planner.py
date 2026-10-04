from typing import Any

from jsonschema import Draft202012Validator
from pydantic import BaseModel, Field, ValidationError

from packages.agent_runtime.gateway import ModelGateway
from packages.agent_runtime.models import ContentPart, ModelRequest
from packages.tools.registry import ToolRegistry

class PlanStep(BaseModel):
    id: str = Field(min_length=1, max_length=128)
    tool: str = Field(min_length=1, max_length=256)
    arguments: dict[str, Any] = Field(default_factory=dict)
    parallel_group: str | None = Field(default=None, max_length=128)
    depends_on: list[str] = Field(default_factory=list, max_length=200)

class AgentPlan(BaseModel):
    steps: list[PlanStep] = Field(min_length=1, max_length=200)

class Planner:
    """Safe deterministic planner used when no provider planner is configured."""
    def plan(self, prompt: str, max_steps: int = 20) -> list[PlanStep]:
        return [PlanStep(id="final", tool="__final__", arguments={"prompt": prompt})][:max_steps]

class StructuredPlanner:
    """Treat model output as untrusted data and validate every proposed tool action."""

    def __init__(self, gateway: ModelGateway, registry: ToolRegistry):
        self.gateway = gateway
        self.registry = registry

    @staticmethod
    def schema() -> dict[str, Any]:
        return AgentPlan.model_json_schema()

    def validate(self, data: dict[str, Any], max_steps: int = 20) -> list[PlanStep]:
        try:
            plan = AgentPlan.model_validate(data)
        except ValidationError as exc:
            raise ValueError("invalid_model_plan") from exc
        if len(plan.steps) > max_steps:
            raise ValueError("plan_exceeds_max_steps")

        seen: set[str] = set()
        deps: dict[str, set[str]] = {}
        for step in plan.steps:
            if step.id in seen:
                raise ValueError("duplicate_plan_step_id")
            seen.add(step.id)
            deps[step.id] = set(step.depends_on)
            if step.tool == "__final__":
                if set(step.arguments) != {"prompt"} or not isinstance(step.arguments["prompt"], str):
                    raise ValueError("invalid_final_step")
                continue
            spec = self.registry.get(step.tool)
            if spec is None:
                raise ValueError("model_selected_unregistered_tool")
            if list(Draft202012Validator(spec.input_schema).iter_errors(step.arguments)):
                raise ValueError("model_generated_invalid_tool_arguments")

        unknown = {d for values in deps.values() for d in values if d not in seen}
        if unknown:
            raise ValueError("plan_has_unknown_dependency")
        pending = set(seen)
        completed: set[str] = set()
        while pending:
            ready = {step_id for step_id in pending if deps[step_id].issubset(completed)}
            if not ready:
                raise ValueError("plan_dependency_cycle")
            completed.update(ready)
            pending.difference_update(ready)
        return plan.steps

    async def plan(self, prompt: str, *, model: str,
                   reasoning_effort: str = "medium", max_steps: int = 20) -> list[PlanStep]:
        request = ModelRequest(
            input=[ContentPart(type="text", data=prompt)],
            model=model,
            reasoning_effort=reasoning_effort,
            response_schema=self.schema(),
        )
        response = await self.gateway.generate_routed(request, min_context=len(prompt))
        if response.structured_output is None:
            raise ValueError("model_did_not_return_structured_plan")
        return self.validate(response.structured_output, max_steps=max_steps)
