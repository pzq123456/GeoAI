"""Run one end-to-end GeoAI analysis against a running backend and record it.

The script posts a designed task to ``POST /api/chat``, consumes the SSE stream,
prints a compact summary, and leaves reproducible records under
``docs/records/`` (raw SSE frames + parsed event summary).

Prerequisite:
    .venv/Scripts/python.exe -m src.main     # backend on 127.0.0.1:8000

Usage:
    .venv/Scripts/python.exe scripts/run_analysis_smoke.py
    .venv/Scripts/python.exe scripts/run_analysis_smoke.py --query "..." --name my-run
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path
from typing import Any

# Windows consoles default to GBK; force UTF-8 so Chinese reports print safely.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
RECORD_DIR = ROOT / "docs" / "records"

DEFAULT_QUERY = (
    "请使用 hk-health 图层完成一次分析：先检索 hospital 分类的设施，"
    "再以第一个医院为中心查询它 800 米范围内还有哪些医疗设施，"
    "然后对附近的医院计算凸包范围，"
    "最后给出分析报告并注明距离/面积单位。"
)


def post_chat(url: str, query: str, timeout: int = 180) -> list[dict[str, Any]]:
    body = json.dumps({"query": query, "history": [], "context": {}}).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", "Accept": "text/event-stream"},
        method="POST",
    )
    events: list[dict[str, Any]] = []
    with urllib.request.urlopen(request, timeout=timeout) as response:
        for raw_line in response:
            line = raw_line.decode("utf-8", errors="replace").strip()
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            try:
                events.append(json.loads(payload))
            except json.JSONDecodeError:
                events.append({"type": "unparsed", "raw": payload})
    return events


def summarise(events: list[dict[str, Any]]) -> dict[str, Any]:
    tool_calls: list[dict[str, Any]] = []
    tool_results: list[dict[str, Any]] = []
    statuses: list[str] = []
    final: dict[str, Any] | None = None
    errors: list[dict[str, Any]] = []

    for event in events:
        kind = event.get("type")
        if kind == "tool_call":
            tool_calls.append({
                "tool": event.get("tool_name"),
                "call_id": event.get("call_id"),
                "arguments": event.get("arguments"),
            })
        elif kind == "tool_result":
            tool_results.append({
                "tool": event.get("tool_name"),
                "status": event.get("status"),
                "latency_ms": event.get("latency_ms"),
                "error": event.get("error"),
            })
        elif kind == "status":
            statuses.append(str(event.get("message", "")))
        elif kind == "final":
            final = event.get("result")
        elif kind in {"error", "unparsed"}:
            errors.append(event)

    return {
        "event_count": len(events),
        "run_id": next((e.get("run_id") for e in events if e.get("run_id")), None),
        "statuses": statuses,
        "tool_calls": tool_calls,
        "tool_results": tool_results,
        "final": final,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000/api/chat")
    parser.add_argument("--query", default=DEFAULT_QUERY)
    parser.add_argument("--name", default="hk-health-analysis")
    args = parser.parse_args()

    print("TASK:", args.query)
    events = post_chat(args.url, args.query)
    summary = summarise(events)

    RECORD_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = RECORD_DIR / f"{args.name}.sse.jsonl"
    summary_path = RECORD_DIR / f"{args.name}.summary.json"
    raw_path.write_text(
        "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in events), encoding="utf-8"
    )
    summary_path.write_text(
        json.dumps(
            {"query": args.query, "url": args.url, "summary": summary},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"\nEVENTS: {summary['event_count']}  run_id={summary['run_id']}")
    print("\nTOOL CALLS:")
    for call in summary["tool_calls"]:
        print(f"  - {call['tool']}({json.dumps(call['arguments'], ensure_ascii=False)})")
    print("\nTOOL RESULTS:")
    for result in summary["tool_results"]:
        print(f"  - {result['tool']}: {result['status']} ({result['latency_ms']}ms)")
    if summary["errors"]:
        print("\nERRORS:")
        for error in summary["errors"]:
            print("  -", json.dumps(error, ensure_ascii=False)[:500])
    print("\nFINAL REPORT:")
    final = summary["final"] or {}
    print((final.get("final_report") or json.dumps(final, ensure_ascii=False))[:2000])
    print("\nRECORDS:", raw_path, summary_path)
    return 0 if final and not summary["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
