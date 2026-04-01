# src/agent.py
import json
import asyncio
from typing import Any, AsyncGenerator
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic_ai.messages import ModelMessagesTypeAdapter

from src.schema import ChatRequest, GISDependencies, GeoDataLoader
from src.agent import gis_expert

app = FastAPI(title="GeoAI API Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/chat")
async def chat_handler(request: ChatRequest):
    async def sse_producers() -> AsyncGenerator[str, None]:
        status_list: list[str] = []
        deps = GISDependencies(loader=GeoDataLoader(), status_updates=status_list)
        
        # 统一的序列化工具
        def sse_msg(data_type: str, payload: Any):
            # 这里统一 dumps 一次，确保非 ASCII 字符（中文）不被转义
            json_str = json.dumps({'type': data_type, 'data': payload}, ensure_ascii=False)
            return f"data: {json_str}\n\n"

        yield sse_msg("status", "GIS 专家正在思考...")

        try:
            # 转换历史记录
            validated_history = ModelMessagesTypeAdapter.validate_python(request.history)
        except Exception:
            validated_history = []

        # 运行 Agent
        task = asyncio.create_task(gis_expert.run(
            request.query, 
            deps=deps, 
            message_history=validated_history
        ))

        # 轮询状态更新
        while not task.done():
            while status_list:
                yield sse_msg("status", status_list.pop(0))
            await asyncio.sleep(0.2)

        try:
            result = await task
            # 组装最终结果。注意：new_history 被转回 Python 对象，方便后续统一 dumps
            response_payload = {
                "report": result.output.model_dump() if hasattr(result.output, 'model_dump') else result.output,
                "geojson": deps.visual_buffer,
                "new_history": json.loads(result.new_messages_json().decode()) 
            }
            yield sse_msg("final_result", response_payload)
        except Exception as e:
            yield sse_msg("error", f"分析中断: {str(e)}")

    return StreamingResponse(sse_producers(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)