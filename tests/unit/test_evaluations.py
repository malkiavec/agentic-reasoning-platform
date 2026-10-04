import pytest
from packages.evaluations.runner import EvaluationCase, EvaluationRunner

@pytest.mark.asyncio
async def test_evaluation_runner_scores_cases():
    async def execute(case):
        return case.prompt.upper()

    results = await EvaluationRunner(execute).run(
        [EvaluationCase("uppercase", "ok")],
        lambda case, output: 1.0 if output == "OK" else 0.0,
    )
    assert results[0].passed
    assert results[0].score == 1.0
