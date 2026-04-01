import json
import asyncio
from typing import Any, AsyncGenerator
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic_ai.messages import ModelMessagesTypeAdapter

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
        # 1. 初始化依赖
        deps = GISDependencies(loader=GeoDataLoader())
        
        def sse_msg(data_type: str, payload: Any):
            json_str = json.dumps({'type': data_type, 'data': payload}, ensure_ascii=False)
            return f"data: {json_str}\n\n"

        # 2. 验证历史记录
        try:
            validated_history = ModelMessagesTypeAdapter.validate_python(request.history)
        except Exception:
            validated_history = []

        # 3. 启动异步任务
        # 使用 run() 获取 AgentRunResult
        run_task = asyncio.create_task(gis_expert.run(
            request.query, 
            deps=deps, 
            message_history=validated_history
        ))

        # 4. 实时状态推送循环
        while not run_task.done():
            try:
                # 检查工具产生的状态消息
                status_msg = await asyncio.wait_for(deps.status_queue.get(), timeout=0.1)
                yield sse_msg("status", status_msg)
            except (asyncio.TimeoutError, asyncio.QueueEmpty):
                continue

        # 5. 处理最终结果
        try:
            result = await run_task
            
            # 【核心修正】根据文档，AgentRunResult 的数据属性是 .output 而非 .data
            final_data = result.output
            
            # 处理历史记录 (使用官方 Adapter 序列化)
            full_history = validated_history + result.new_messages()
            history_json_bytes = ModelMessagesTypeAdapter.dump_json(full_history)
            history_for_payload = json.loads(history_json_bytes)

            # 组装返回载荷
            response_payload = {
                # 对结构化模型进行 model_dump
                "report": final_data.model_dump() if hasattr(final_data, 'model_dump') else final_data,
                "geojson": deps.visual_buffer, 
                "new_history": history_for_payload 
            }
            yield sse_msg("final_result", response_payload)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            yield sse_msg("error", f"GIS 分析失败: {str(e)}")

    return StreamingResponse(sse_producers(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)