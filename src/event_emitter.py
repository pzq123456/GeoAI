"""Per-run event emitter and SSE serialization."""

import asyncio
import json
from typing import Any
from uuid import uuid4

from pydantic import TypeAdapter

from .events import AgentEvent, ErrorDetail, TERMINAL_TYPES

_event_adapter = TypeAdapter(AgentEvent)


class EventEmitter:
    """Assign run metadata and monotonically increasing sequence numbers."""

    def __init__(self, run_id: str | None = None):
        self.run_id = run_id or str(uuid4())
        self._sequence = 0
        self._terminal_emitted = False
        self.queue: asyncio.Queue[str] = asyncio.Queue()

    def emit(self, event: AgentEvent) -> AgentEvent:
        if self._terminal_emitted:
            raise RuntimeError("Cannot emit events after a terminal event")
        self._sequence += 1
        updated = event.model_copy(update={
            "run_id": self.run_id,
            "sequence": self._sequence,
            "event_id": str(uuid4()),
        })
        if event.type in TERMINAL_TYPES:
            self._terminal_emitted = True
        self.queue.put_nowait(self.to_sse(updated))
        return updated

    def status(self, message: str, stage: str | None = None) -> AgentEvent:
        from .events import StatusEvent
        return self.emit(StatusEvent(type="status", message=message, stage=stage))

    def tool_call(self, tool_name: str, call_id: str, arguments: dict[str, Any]) -> AgentEvent:
        from .events import ToolCallEvent
        return self.emit(ToolCallEvent(
            type="tool_call",
            tool_name=tool_name,
            call_id=call_id,
            arguments=arguments,
        ))

    def tool_result(
        self,
        tool_name: str,
        call_id: str,
        latency_ms: int,
        *,
        result_ref: str | None = None,
        error: ErrorDetail | None = None,
    ) -> AgentEvent:
        from .events import ToolResultEvent
        return self.emit(ToolResultEvent(
            type="tool_result",
            tool_name=tool_name,
            call_id=call_id,
            status="error" if error else "success",
            latency_ms=latency_ms,
            result_ref=result_ref,
            error=error,
        ))

    def final(self, result: dict[str, Any], artifact_refs: list[str] | None = None) -> AgentEvent:
        from .events import FinalEvent
        return self.emit(FinalEvent(
            type="final",
            result=result,
            artifact_refs=artifact_refs or [],
        ))

    def error(self, code: str, message: str, retryable: bool = False) -> AgentEvent:
        from .events import ErrorEvent
        return self.emit(ErrorEvent(
            type="error", code=code, message=message, retryable=retryable
        ))

    @staticmethod
    def to_sse(event: AgentEvent) -> str:
        """One event per SSE frame, UTF-8 friendly."""
        payload = json.dumps(event.model_dump(mode="json"), ensure_ascii=False)
        return f"data: {payload}\n\n"

    @staticmethod
    def parse(raw: str) -> AgentEvent:
        return _event_adapter.validate_python(json.loads(raw))
