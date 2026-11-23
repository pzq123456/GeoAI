import json

import pytest
from fastapi.testclient import TestClient

import src.main as main


def _events(text: str):
    events = []
    for block in text.split("\n\n"):
        line = block.strip()
        if line.startswith("data: "):
            events.append(json.loads(line[len("data: "):]))
    return events


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(main, "MOCK_MODE", True)
    return TestClient(main.app)


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["mode"] == "mock"
    assert body["event_schema_version"] == "1.0"


def test_mock_chat_emits_unified_event_contract(client):
    response = client.post("/api/chat", json={"query": "分析 tree 图层", "history": []})
    assert response.status_code == 200
    events = _events(response.text)
    types = [e["type"] for e in events]

    assert "status" in types
    assert "tool_call" in types
    assert "tool_result" in types
    assert types[-1] == "final"
    assert "final_result" not in types

    # sequence and run_id consistency
    assert [e["sequence"] for e in events] == list(range(1, len(events) + 1))
    assert len({e["run_id"] for e in events}) == 1
    assert all(e["schema_version"] == "1.0" for e in events)
    assert len({e["event_id"] for e in events}) == len(events)

    # tool call/result pairing
    calls = [e for e in events if e["type"] == "tool_call"]
    results = [e for e in events if e["type"] == "tool_result"]
    assert [c["call_id"] for c in calls] == [r["call_id"] for r in results]
    assert {c["tool_name"] for c in calls} >= {"list_layers", "query_layer_features"}
    assert all(r["latency_ms"] >= 0 for r in results)
    assert all(r["status"] == "success" for r in results)

    final = events[-1]["data"] if "data" in events[-1] else events[-1]["result"]
    assert final["geojson"]["type"] == "FeatureCollection"
    assert len(final["geojson"]["features"]) >= 20
    assert final["report"]["visualization_status"] == "ok"


def test_empty_query_is_rejected(client):
    response = client.post("/api/chat", json={"query": "", "history": []})
    assert response.status_code == 422


def test_error_event_is_sanitized(client, monkeypatch):
    async def boom(*args, **kwargs):
        raise RuntimeError("boom with /secret/path")

    monkeypatch.setattr(main, "run_with_events", boom)
    response = client.post("/api/chat", json={"query": "x", "history": []})
    events = _events(response.text)

    assert events[-1]["type"] == "error"
    assert events[-1]["code"] == "RUN_EXECUTION_ERROR"
    assert "boom" not in events[-1]["message"]
    assert "/secret/path" not in events[-1]["message"]
