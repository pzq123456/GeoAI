import pytest
from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel
from pydantic_ai.messages import ToolCallPart

from src.agent import GIS_TOOLS
from src.prompts import get_system_instructions
from src.schema import GISAnalysisOutput, ClarificationResponse


@pytest.mark.asyncio
async def test_testmodel_multi_step_tool_execution(deps):
    """No token required: TestModel drives the real agent + tool registry."""
    agent = Agent(
        TestModel(),
        deps_type=type(deps),
        output_type=GISAnalysisOutput | ClarificationResponse,
        instructions=get_system_instructions(),
        tools=GIS_TOOLS,
        retries=2,
    )

    result = await agent.run("list layers and measure a tree", deps=deps)

    assert isinstance(result.output, (GISAnalysisOutput, ClarificationResponse))
    calls = [
        part.tool_name
        for message in result.new_messages()
        for part in getattr(message, "parts", [])
        if isinstance(part, ToolCallPart)
    ]
    assert calls[0] == "list_layers"
    assert len(calls) >= 2  # genuinely multi-step, not a single tool call
    assert not deps.status_queue.empty()  # tools pushed SSE status events
