"""Phase 1 event contract.

Pydantic v2 models are the single source of truth for GeoAI run events.
Generated JSON Schema and TypeScript types are derived from these models.
"""

from datetime import datetime, timezone
from typing import Annotated, Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator

SCHEMA_VERSION = "1.0"


class EventBase(BaseModel):
    schema_version: Literal["1.0"] = SCHEMA_VERSION
    # Defaults let callers construct typed events before the emitter stamps
    # run-scoped metadata; emitter.emit() always overwrites these values.
    run_id: str = Field(default_factory=lambda: str(uuid4()), min_length=1)
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    sequence: int = Field(default=1, ge=1)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def _timestamp_must_be_utc_aware(self):
        if self.timestamp.tzinfo is None or self.timestamp.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware")
        return self


class ErrorDetail(BaseModel):
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    retryable: bool = False


class StatusEvent(EventBase):
    type: Literal["status"]
    message: str
    stage: str | None = None


class ToolCallEvent(EventBase):
    type: Literal["tool_call"]
    tool_name: str = Field(min_length=1)
    call_id: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolResultEvent(EventBase):
    type: Literal["tool_result"]
    tool_name: str = Field(min_length=1)
    call_id: str = Field(min_length=1)
    status: Literal["success", "error"]
    latency_ms: int = Field(ge=0)
    result_ref: str | None = None
    error: ErrorDetail | None = None

    @model_validator(mode="after")
    def _error_consistency(self):
        if self.status == "error" and self.error is None:
            raise ValueError("error status requires error detail")
        if self.status == "success" and self.error is not None:
            raise ValueError("success status cannot carry error detail")
        return self


class FinalEvent(EventBase):
    type: Literal["final"]
    result: dict[str, Any] = Field(default_factory=dict)
    artifact_refs: list[str] = Field(default_factory=list)


class ErrorEvent(EventBase):
    type: Literal["error"]
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    retryable: bool = False


AgentEvent = Annotated[
    StatusEvent | ToolCallEvent | ToolResultEvent | FinalEvent | ErrorEvent,
    Field(discriminator="type"),
]

TERMINAL_TYPES = frozenset({"final", "error"})
