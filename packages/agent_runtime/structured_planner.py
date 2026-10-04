from pydantic import BaseModel, Field

class PlanStep(BaseModel):
    id: str = Field(min_length=1, max_length=128)
    tool: str = Field(min_length=1, max_length=256)
    arguments: dict = Field(default_factory=dict)
    parallel_group: str | None = None

class AgentPlan(BaseModel):
    steps: list[PlanStep] = Field(min_length=1, max_length=200)
