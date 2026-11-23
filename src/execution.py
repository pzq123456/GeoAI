"""Agent execution with official Pydantic AI graph-node event instrumentation."""

import asyncio
import json
import time
from typing import Any


def _coerce_args(value: Any) -> dict[str, Any]:
    """Normalise tool-call arguments to a dict before emitting events.

    Real OpenAI-compatible models (e.g. DeepSeek) serialise function arguments
    as a JSON *string* (``'{"layer_name": "hk-health"}'``), whereas the mock
    FunctionModel passes a dict directly. The Pydantic ToolCallEvent schema
    requires a dict, so parse strings here. Never let a malformed arg crash the
    whole SSE stream — fall back to an empty dict.
    """
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except (ValueError, TypeError):
            pass
    return {}


from pydantic_ai import Agent
from pydantic_ai.messages import (
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    RetryPromptPart,
    ToolCallPart,
    ModelResponse,
)
from pydantic_ai.models.function import FunctionModel

from .agent import gis_expert
from .artifacts import ArtifactStore
from .event_emitter import EventEmitter
from .events import ErrorDetail
from .schema import DATA_DIR, GISDependencies
from .utils.geo_ops import generate_stable_id
from .utils.logger import logger


async def drain_status(deps: GISDependencies, emitter: EventEmitter) -> None:
    """Tools still push status strings; the execution layer emits them as events."""
    while True:
        try:
            message = deps.status_queue.get_nowait()
        except asyncio.QueueEmpty:
            return
        emitter.status(message)


async def run_with_events(
    query: str,
    deps: GISDependencies,
    emitter: EventEmitter,
    artifacts: ArtifactStore,
    *,
    model=None,
    message_history=None,
):
    """Run the existing agent and emit real tool-call/tool-result events.

    Uses the official API verified in Phase 1.0:
    Agent.iter -> Agent.is_call_tools_node -> node.stream(run.ctx).
    No tool wrappers are used.
    """
    async with gis_expert.iter(
        query,
        deps=deps,
        message_history=message_history,
        model=model,
    ) as run:
        async for node in run:
            await drain_status(deps, emitter)

            if Agent.is_call_tools_node(node):
                call_names: dict[str, str] = {}
                call_started: dict[str, float] = {}
                completed: set[str] = set()
                node_started = time.perf_counter()

                try:
                    async with node.stream(run.ctx) as stream:
                        async for event in stream:
                            if isinstance(event, FunctionToolCallEvent):
                                call_id = event.part.tool_call_id
                                call_names[call_id] = event.part.tool_name
                                call_started[call_id] = time.perf_counter()
                                emitter.tool_call(
                                    event.part.tool_name,
                                    call_id,
                                    _coerce_args(event.part.args),
                                )
                                await drain_status(deps, emitter)
                            elif isinstance(event, FunctionToolResultEvent):
                                call_id = event.result.tool_call_id
                                tool_name = call_names.get(call_id, event.result.tool_name)
                                latency_ms = max(
                                    0,
                                    int((time.perf_counter() - call_started.get(
                                        call_id, node_started)) * 1000),
                                )
                                if isinstance(event.result, RetryPromptPart):
                                    ref = artifacts.save(
                                        {"content": str(event.result.content)},
                                        "tool_validation",
                                    )
                                    emitter.tool_result(
                                        tool_name, call_id, latency_ms,
                                        result_ref=ref,
                                        error=ErrorDetail(
                                            code="TOOL_ARGUMENT_INVALID",
                                            message="Tool arguments were invalid; retrying.",
                                            retryable=True,
                                        ),
                                    )
                                else:
                                    ref = artifacts.save(
                                        {
                                            "tool_name": tool_name,
                                            "content": event.result.content,
                                        },
                                        "tool_result",
                                    )
                                    emitter.tool_result(
                                        tool_name, call_id, latency_ms, result_ref=ref
                                    )
                                completed.add(call_id)
                                await drain_status(deps, emitter)
                except Exception:
                    failed_id = next(
                        (cid for cid in call_names if cid not in completed), None
                    )
                    if failed_id is not None:
                        latency_ms = max(
                            0,
                            int((time.perf_counter() - call_started.get(
                                failed_id, node_started)) * 1000),
                        )
                        logger.exception(f"tool execution failed: {call_names[failed_id]}")
                        emitter.tool_result(
                            call_names[failed_id], failed_id, latency_ms,
                            error=ErrorDetail(
                                code="TOOL_EXECUTION_ERROR",
                                message="Tool execution failed.",
                                retryable=False,
                            ),
                        )
                    raise

                await drain_status(deps, emitter)

            if Agent.is_end_node(node):
                break
            await run.next(node)

        await drain_status(deps, emitter)
        return run.result


def _mock_layer_plan(loader, layer_name: str) -> tuple[str, list[str]]:
    """Pick a real category and real feature IDs from a discovered layer.

    The original mock plan was hard-coded for the retired ``tree`` layer
    (``T03562`` / ``tree:1``). Deriving them from the actual layer keeps the
    offline demo working on the Hong Kong open-data layers.
    """
    category = ""
    meta_path = DATA_DIR / "meta" / f"{layer_name}.meta.json"
    if meta_path.exists():
        try:
            counts = json.loads(meta_path.read_text(encoding="utf-8")).get("counts") or {}
            category = next(iter(counts), "")
        except (OSError, ValueError):
            category = ""

    data = loader.load_geojson(f"{layer_name}.json")
    features = data.get("features", [])
    if category:
        features = [f for f in features if f.get("properties", {}).get("category") == category]
    if not features:
        return category, []

    def xy(feature):
        coords = feature.get("geometry", {}).get("coordinates") or [0, 0]
        return coords[0], coords[1]

    source = features[0]
    ox, oy = xy(source)
    rest = features[1:]
    # Nearest neighbours keep the demo's convex hull local instead of spanning
    # the whole territory (the mirror's files are not spatially sorted).
    rest.sort(key=lambda f: (xy(f)[0] - ox) ** 2 + (xy(f)[1] - oy) ** 2)
    selected = [source, *rest[:3]]
    ids = [generate_stable_id(layer_name, f, i) for i, f in enumerate(selected)]
    return category, ids


def build_mock_model(
    query: str,
    layer_name: str,
    final_result: dict[str, Any],
    loader=None,
) -> FunctionModel:
    """Deterministic FunctionModel for the existing mock mode.

    Tool calls are executed by the real GIS tools through the same Agent path,
    so the generated events are genuine Pydantic AI tool events.
    """
    category, ids = _mock_layer_plan(loader, layer_name) if loader else ("", [])
    source_id = ids[0] if ids else f"{layer_name}:1"
    hull_ids = ids[:4] if ids else [f"{layer_name}:{i}" for i in range(1, 5)]

    calls = [
        ToolCallPart(tool_name="list_layers", args={}),
        ToolCallPart(
            tool_name="query_layer_features",
            args={"layer_name": layer_name, "query": category or "hospital"},
        ),
        ToolCallPart(
            tool_name="spatial_query_nearby",
            args={
                "source_layer": layer_name,
                "source_feature_id": source_id,
                "target_layer": layer_name,
                "radius_m": 800,
                "visualize_buffer": True,
                "limit": 20,
            },
        ),
        ToolCallPart(
            tool_name="calculate_group_convex_hull",
            args={
                "layer_name": layer_name,
                "feature_ids": hull_ids,
            },
        ),
    ]
    state = {"i": 0}

    def handler(messages, info) -> ModelResponse:
        i = state["i"]
        state["i"] += 1
        if i < len(calls):
            return ModelResponse(parts=[calls[i]])
        return ModelResponse(parts=[ToolCallPart(
            tool_name="final_result_GISAnalysisOutput",
            args=final_result,
        )])

    return FunctionModel(handler)
