from datetime import datetime, timezone

import pytest
from pydantic import TypeAdapter, ValidationError

from src.event_emitter import EventEmitter
from src.events import (
    AgentEvent,
    ErrorDetail,
    ErrorEvent,
    FinalEvent,
    StatusEvent,
    ToolCallEvent,
    ToolResultEvent,
)


adapter = TypeAdapter(AgentEvent)


@pytest.mark.parametrize("event", [
    StatusEvent(type="status", message="hi"),
    ToolCallEvent(type="tool_call", tool_name="t", call_id="c", arguments={}),
    ToolResultEvent(type="tool_result", tool_name="t", call_id="c", status="success", latency_ms=0),
    ToolResultEvent(type="tool_result", tool_name="t", call_id="c", status="error",
                    latency_ms=1, error=ErrorDetail(code="E", message="m")),
    FinalEvent(type="final", result={"ok": True}),
    ErrorEvent(type="error", code="E", message="m"),
])
def test_every_event_type_validates(event):
    validated = adapter.validate_python(event.model_dump(mode="python"))
    assert validated.type == event.type
    assert validated.sequence >= 1


def test_unknown_event_type_fails():
    with pytest.raises(ValidationError):
        adapter.validate_python({"type": "unknown", "message": "x"})


def test_tool_result_error_consistency():
    with pytest.raises(ValidationError):
        ToolResultEvent(type="tool_result", tool_name="t", call_id="c",
                        status="success", latency_ms=1,
                        error=ErrorDetail(code="E", message="m"))
    with pytest.raises(ValidationError):
        ToolResultEvent(type="tool_result", tool_name="t", call_id="c",
                        status="error", latency_ms=1)
    with pytest.raises(ValidationError):
        ToolResultEvent(type="tool_result", tool_name="t", call_id="c",
                        status="success", latency_ms=-1)


def test_timestamp_must_be_timezone_aware():
    with pytest.raises(ValidationError):
        StatusEvent(type="status", message="x", timestamp=datetime(2026, 1, 1))


def test_emitter_sequence_and_ids_and_terminal_guard():
    emitter = EventEmitter(run_id="run-1")
    e1 = emitter.status("start")
    e2 = emitter.tool_call("list_layers", "call-1", {})
    e3 = emitter.tool_result("list_layers", "call-1", 5)
    final = emitter.final({"done": True})

    assert [e.sequence for e in (e1, e2, e3, final)] == [1, 2, 3, 4]
    assert len({e.event_id for e in (e1, e2, e3, final)}) == 4
    assert all(e.run_id == "run-1" for e in (e1, e2, e3, final))
    assert e1.timestamp.tzinfo is not None
    with pytest.raises(RuntimeError):
        emitter.status("too late")


def test_sse_roundtrip_unicode():
    frame = EventEmitter.to_sse(EventEmitter().status("检索 [tree] ✓"))
    assert frame.startswith("data: ") and frame.endswith("\n\n")
    parsed = EventEmitter.parse(frame[len("data: "):].strip())
    assert parsed.type == "status"
    assert parsed.message == "检索 [tree] ✓"
