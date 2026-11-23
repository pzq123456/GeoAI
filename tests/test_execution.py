import json

import pytest
from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.tools import Tool

import src.execution as execution
from src.artifacts import ArtifactStore
from src.event_emitter import EventEmitter
from src.schema import GISDependencies, GeoDataLoader


def _frames(emitter):
    return [json.loads(frame[len("data: "):].strip())
            for frame in list(emitter.queue._queue)]


@pytest.mark.asyncio
async def test_tool_exception_emits_error_result_not_success(monkeypatch):
    async def boom(ctx: RunContext[GISDependencies]) -> str:
        raise RuntimeError("intentional failure")

    model = FunctionModel(lambda messages, info: ModelResponse(
        parts=[ToolCallPart(tool_name="boom", args={})]
    ))
    failing_agent = Agent(
        model,
        deps_type=GISDependencies,
        output_type=str,
        tools=[Tool(boom, name="boom", description="fails")],
        retries=0,
    )
    monkeypatch.setattr(execution, "gis_expert", failing_agent)

    emitter = EventEmitter(run_id="run-exc")
    artifacts = ArtifactStore(emitter.run_id)
    deps = GISDependencies(loader=GeoDataLoader())

    with pytest.raises(RuntimeError, match="intentional failure"):
        await execution.run_with_events("x", deps, emitter, artifacts)

    events = _frames(emitter)
    calls = [e for e in events if e["type"] == "tool_call"]
    results = [e for e in events if e["type"] == "tool_result"]
    assert len(calls) == 1
    assert len(results) == 1
    assert results[0]["status"] == "error"
    assert results[0]["error"]["code"] == "TOOL_EXECUTION_ERROR"
    assert results[0]["call_id"] == calls[0]["call_id"]
    assert "intentional failure" not in json.dumps(results[0])


@pytest.mark.asyncio
async def test_validation_failure_emits_retryable_error_result(monkeypatch):
    async def needs_arg(ctx: RunContext[GISDependencies], value: int) -> str:
        return str(value)

    model = FunctionModel(lambda messages, info: ModelResponse(
        parts=[ToolCallPart(tool_name="needs_arg", args={})]
    ))
    agent = Agent(
        model,
        deps_type=GISDependencies,
        output_type=str,
        tools=[Tool(needs_arg, name="needs_arg", description="needs int")],
        retries=1,
    )
    monkeypatch.setattr(execution, "gis_expert", agent)

    emitter = EventEmitter(run_id="run-validation")
    artifacts = ArtifactStore(emitter.run_id)
    deps = GISDependencies(loader=GeoDataLoader())

    with pytest.raises(Exception):
        await execution.run_with_events("x", deps, emitter, artifacts)

    results = [e for e in _frames(emitter) if e["type"] == "tool_result"]
    assert results
    assert results[0]["status"] == "error"
    assert results[0]["error"]["code"] == "TOOL_ARGUMENT_INVALID"
    assert results[0]["error"]["retryable"] is True
