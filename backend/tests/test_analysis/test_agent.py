import pytest
from app.analysis.agent import run_analysis


@pytest.mark.asyncio
async def test_analysis_agent():
    raw = {"idea": "A forensic pathologist travels to ancient China to investigate serial murders", "constraints": "Science-based reasoning only"}
    result = await run_analysis(raw)
    assert result.metadata.core_conflict != ""
