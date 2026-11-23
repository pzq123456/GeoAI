# src\main.py

import asyncio
import json
import os
from contextlib import suppress
from pathlib import Path
from typing import Any, AsyncGenerator
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic_ai.messages import ModelMessagesTypeAdapter
from dotenv import load_dotenv

# --- 1. 核心接管步骤：必须在导入其他业务模块前初始化 ---
from src.utils.logger import logger, setup_app_logging
setup_app_logging()

# .env 必须在 agent.py 读取 DEEPSEEK_API_KEY 之前加载
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)
# ---------------------------------------------------

from src.artifacts import ArtifactStore
from src.event_emitter import EventEmitter
from src.execution import build_mock_model, drain_status, run_with_events
from src.schema import ChatRequest, GISDependencies, GeoDataLoader

MODEL_TIMEOUT_S = float(os.getenv("GEOAI_MODEL_TIMEOUT", "90"))

app = FastAPI(title="GeoAI Professional Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _use_mock_model() -> bool:
    """Run the deterministic offline demo when no usable key is configured."""
    override = os.getenv("GEOAI_MOCK", "").strip().lower()
    if override in {"0", "false", "no"}:
        return False
    if override in {"1", "true", "yes"}:
        return True
    key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    return not key or len(key) < 20 or "xxxx" in key.lower() or "your" in key.lower()


MOCK_MODE = _use_mock_model()


def _mock_final_result(query: str, layer_name: str) -> dict[str, Any]:
    return {
        "analysis_steps": [
            f"列出图层（发现 {layer_name} 等）",
            f"在 {layer_name} 中检索设施",
            "以检索到的首个设施为中心做 800m 邻近查询",
            "对前 4 个命中设施计算凸包范围",
        ],
        "final_report": (
            f"> **演示任务**：在 `{layer_name}` 图层中定位设施，"
            f"检索其 800m 范围内的同类设施，并计算前 4 个设施的凸包范围。\n\n"
            f"所有步骤均由真实 GIS 工具在真实数据上执行；"
            f"当前使用本地确定性脚本模型编排工具（未调用付费大模型）。"
        ),
        "visualization_status": "ok",
    }


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "mode": "mock" if MOCK_MODE else "live",
        "key_configured": bool(os.getenv("DEEPSEEK_API_KEY", "").strip()),
        "event_schema_version": "1.0",
    }


@app.post("/api/chat")
async def chat_handler(request: ChatRequest):
    """Stream one agent run as unified AgentEvent SSE frames."""
    emitter = EventEmitter()
    artifacts = ArtifactStore(emitter.run_id)

    async def sse_producers() -> AsyncGenerator[str, None]:
        logger.info(f"[{emitter.run_id}] 收到请求 - Query: {request.query}")

        deps = GISDependencies(loader=GeoDataLoader(), context=request.context)

        def drain_frames():
            frames = []
            while not emitter.queue.empty():
                frames.append(emitter.queue.get_nowait())
            return frames

        try:
            validated_history = ModelMessagesTypeAdapter.validate_python(request.history)
        except Exception:
            logger.warning(f"[{emitter.run_id}] 历史记录验证失败，已重置为空")
            validated_history = []

        task = None
        try:
            emitter.status("正在分析用户请求", stage="start")
            model = None
            layer_name = "tree"
            if MOCK_MODE:
                layers = [f.stem for f in deps.loader.base_path.glob("*.json")]
                layer_name = next(
                    (name for name in layers if name in request.query.lower()),
                    layers[0] if layers else "tree",
                )
                model = build_mock_model(
                    request.query,
                    layer_name,
                    _mock_final_result(request.query, layer_name),
                    deps.loader,
                )

            task = asyncio.create_task(asyncio.wait_for(
                run_with_events(
                    request.query,
                    deps,
                    emitter,
                    artifacts,
                    model=model,
                    message_history=validated_history,
                ),
                timeout=MODEL_TIMEOUT_S,
            ))

            # Stream frames while the agent runs.
            while not task.done():
                for frame in drain_frames():
                    yield frame
                await asyncio.sleep(0.01)
            for frame in drain_frames():
                yield frame

            result = await task
            await drain_status(deps, emitter)

            combined_geojson = None
            if deps.visual_staging:
                combined_geojson = {
                    "type": "FeatureCollection",
                    "features": deps.visual_staging,
                }

            full_history = validated_history + result.new_messages()
            history_for_payload = ModelMessagesTypeAdapter.dump_json(full_history)

            payload = {
                "report": result.output.model_dump(),
                "geojson": combined_geojson,
                "new_history": json.loads(history_for_payload),
            }
            emitter.final(payload)
            logger.success(f"[{emitter.run_id}] GIS 分析任务圆满完成")
            for frame in drain_frames():
                yield frame

        except Exception:
            logger.exception(f"[{emitter.run_id}] GIS 分析失败")
            if not emitter._terminal_emitted:
                emitter.error(
                    code="RUN_EXECUTION_ERROR",
                    message="GIS analysis failed. See server logs for details.",
                    retryable=False,
                )
            for frame in drain_frames():
                yield frame
        finally:
            if task is not None and not task.done():
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task

    return StreamingResponse(sse_producers(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("GEOAI_HOST", "127.0.0.1")
    uvicorn.run(app, host=host, port=8000)
