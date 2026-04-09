# src\main.py

import json
import asyncio
from typing import Any, AsyncGenerator
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic_ai.messages import ModelMessagesTypeAdapter

# --- 1. 核心接管步骤：必须在导入其他业务模块前初始化 ---
from src.utils.logger import logger, setup_app_logging
setup_app_logging() 
# ---------------------------------------------------

from src.schema import ChatRequest, GISDependencies, GeoDataLoader
from src.agent import gis_expert

app = FastAPI(title="GeoAI Professional Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/chat")
async def chat_handler(request: ChatRequest):
    async def sse_producers() -> AsyncGenerator[str, None]:
        logger.info(f"收到请求 - Query: {request.query}") # 记录请求
        
        deps = GISDependencies(loader=GeoDataLoader())
        
        def sse_msg(data_type: str, payload: Any):
            json_str = json.dumps({'type': data_type, 'data': payload}, ensure_ascii=False)
            return f"data: {json_str}\n\n"

        try:
            validated_history = ModelMessagesTypeAdapter.validate_python(request.history)
        except Exception:
            logger.warning("历史记录验证失败，已重置为空") # 替换 print
            validated_history = []

        run_task = asyncio.create_task(gis_expert.run(
            request.query, 
            deps=deps, 
            message_history=validated_history
        ))

        while not run_task.done():
            try:
                status_msg = await asyncio.wait_for(deps.status_queue.get(), timeout=0.1)
                logger.debug(f"Status Update: {status_msg}") # 记录中间状态
                yield sse_msg("status", status_msg)
            except (asyncio.TimeoutError, asyncio.QueueEmpty):
                continue

        try:
            result = await run_task
            final_data = result.output

            combined_geojson = None
            if deps.visual_staging:
                combined_geojson = {
                    "type": "FeatureCollection",
                    "features": deps.visual_staging
                }

            full_history = validated_history + result.new_messages()
            history_json_bytes = ModelMessagesTypeAdapter.dump_json(full_history)
            history_for_payload = json.loads(history_json_bytes)

            response_payload = {
                "report": final_data.model_dump() if hasattr(final_data, 'model_dump') else final_data,
                "geojson": combined_geojson,
                "new_history": history_for_payload 
            }
            
            logger.success("GIS 分析任务圆满完成") # 成功记录
            yield sse_msg("final_result", response_payload)
            
        except Exception as e:
            # --- 2. 使用 logger.exception 自动捕获堆栈 ---
            logger.exception(f"GIS 分析失败: {str(e)}") 
            yield sse_msg("error", f"GIS 分析失败: {str(e)}")

    return StreamingResponse(sse_producers(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    # 启动时，uvicorn 的所有日志也会被 InterceptHandler 捕获并按 loguru 格式输出
    uvicorn.run(app, host="0.0.0.0", port=8000)