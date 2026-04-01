import os
import json
import asyncio
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Any, Union, Optional, AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.deepseek import DeepSeekProvider

from shapely.geometry import shape, mapping
import pyproj
from shapely.ops import transform

# --- 0. 环境与路径配置 ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

app = FastAPI(title="GeoAI API Service")

# --- 允许跨域配置 ---
app.add_middleware(
    CORSMiddleware,
    # 允许的源（生产环境建议指定具体的域名，开发环境可以用 ["*"]）
    allow_origins=["*"], 
    # 允许携带 Cookie
    allow_credentials=True,
    # 允许的方法（GET, POST, OPTIONS 等）
    allow_methods=["*"],
    # 允许的 Header
    allow_headers=["*"],
)

# --- 1. 数据模型定义 ---

class GeoDataLoader:
    """负责从磁盘加载静态地理数据"""
    def __init__(self, base_dir: Path = DATA_DIR):
        self.base_path = base_dir

    def load_geojson(self, filename: str) -> Dict[str, Any]:
        file_path = self.base_path / filename
        if not file_path.exists():
            raise FileNotFoundError(f"Missing data file: {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def get_transformer(from_crs="EPSG:4326", to_crs="EPSG:3857"):
        return pyproj.Transformer.from_crs(from_crs, to_crs, always_xy=True).transform

@dataclass
class GISDependencies:
    """AI 运行时的依赖项，包含内存缓冲区"""
    loader: GeoDataLoader
    # 核心：用于暂存 GeoJSON 数据，不写磁盘
    visual_buffer: Optional[Dict[str, Any]] = None
    # 模拟一个消息队列，用于将工具内部状态发给 SSE
    status_updates: List[str] = None 

    def add_status(self, msg: str):
        if self.status_updates is not None:
            self.status_updates.append(msg)

# AI 输出结构
class ClarificationResponse(BaseModel):
    guidance: str
    suggestions: List[str]

class GISAnalysisOutput(BaseModel):
    analysis_steps: List[str]
    final_report: str
    visualization_status: str

# API 请求结构
class ChatRequest(BaseModel):
    query: str
    history: List[Dict[str, Any]] = []
    # 允许前端透传用户选中的要素 JSON
    context_features: Optional[Dict[str, Any]] = None

# --- 2. Agent 定义 ---

model = OpenAIChatModel(
    model_name='deepseek-chat',
    provider=DeepSeekProvider(api_key=os.getenv('DEEPSEEK_API_KEY')),
)

gis_expert = Agent(
    model=model,
    deps_type=GISDependencies,
    output_type=Union[GISAnalysisOutput, ClarificationResponse],
    instructions=[
        "你是一个专业 GIS 专家。如果用户提供了 context_features，请优先分析该要素。",
        "在执行复杂空间计算前，请调用工具。分析完成后，务必调用 save_to_visualization_layer 发送地理结果。",
        "如果信息不足，请引导用户提供具体 ID 或点击地图对象。"
    ],
)

# --- 3. 工具箱 ---

@gis_expert.tool
async def list_available_features(ctx: RunContext[GISDependencies]) -> str:
    """列出 park.json 中可用的地理要素。"""
    ctx.deps.add_status("正在检索地块数据库...")
    try:
        data = ctx.deps.loader.load_geojson("park.json")
        ids = [f.get("id") or f.get("properties", {}).get("@id") for f in data.get('features', [])]
        return f"可用要素 ID 列表: {', '.join(filter(None, ids))}"
    except Exception as e:
        return f"数据加载失败: {str(e)}"

@gis_expert.tool
async def get_proximity_data(ctx: RunContext[GISDependencies], target_id: str, radius: float, category: str) -> Dict[str, Any]:
    """执行空间缓冲区分析。"""
    ctx.deps.add_status(f"正在对 {target_id} 执行 {radius}米 缓冲区分析...")
    try:
        park_data = ctx.deps.loader.load_geojson("park.json")
        poi_data = ctx.deps.loader.load_geojson("poi.json")
        to_meters = ctx.deps.loader.get_transformer()
        to_degrees = ctx.deps.loader.get_transformer("EPSG:3857", "EPSG:4326")
        
        target_f = next((f for f in park_data['features'] if (f.get("id") or f.get("properties", {}).get("@id")) == target_id), None)
        if not target_f: return {"error": "未找到 ID"}

        geom_meters = transform(to_meters, shape(target_f['geometry']))
        buffer_poly = geom_meters.buffer(radius)
        buffer_wgs = transform(to_degrees, buffer_poly)
        
        # 简化版 POI 筛选
        hits = [p for p in poi_data['features'] if transform(to_meters, shape(p['geometry'])).within(buffer_poly)]

        return {
            "area_m2": round(geom_meters.area, 2),
            "poi_count": len(hits),
            "visual_packet": {
                "type": "FeatureCollection",
                "features": [
                    {"type": "Feature", "geometry": mapping(buffer_wgs), "properties": {"layer": "buffer"}},
                    *hits
                ]
            }
        }
    except Exception as e:
        return {"error": str(e)}

@gis_expert.tool
async def save_to_visualization_layer(ctx: RunContext[GISDependencies], geojson_data: Dict[str, Any]) -> str:
    """【无写盘版】将 GeoJSON 数据推送到前端。"""
    ctx.deps.visual_buffer = geojson_data
    ctx.deps.add_status("空间可视化图层准备完毕。")
    return "✅ 数据已进入渲染缓冲区"

# --- 4. FastAPI SSE 接口 ---

@app.post("/api/chat")
async def chat_handler(request: ChatRequest):
    async def sse_producers() -> AsyncGenerator[str, None]:
        # 初始化依赖
        status_list = []
        deps = GISDependencies(loader=GeoDataLoader(), status_updates=status_list)
        
        # 辅助函数：格式化 SSE 消息
        def sse_msg(data_type: str, payload: Any):
            return f"data: {json.dumps({'type': data_type, 'data': payload}, ensure_ascii=False)}\n\n"

        yield sse_msg("status", "GIS 专家正在思考...")

        # 创建后台任务运行 Agent
        # 提示：由于 Pydantic AI 的流式主要是针对文本，
        # 我们这里采用“轮询状态队列 + 等待最终结果”的策略来模拟流式感知
        task = asyncio.create_task(gis_expert.run(
            request.query, 
            deps=deps, 
            message_history=request.history
        ))

        # 只要任务没完成，就检查是否有新的状态更新
        while not task.done():
            while status_list:
                yield sse_msg("status", status_list.pop(0))
            await asyncio.sleep(0.5) # 避免空转

        try:
            result = await task
            # 组装最终结果
            response_payload = {
                "report": result.output.model_dump(),
                "geojson": deps.visual_buffer, # 此时已由工具填入内容
                "new_history": result.new_messages_json().decode()
            }
            yield sse_msg("final_result", response_payload)
        except Exception as e:
            yield sse_msg("error", f"分析中断: {str(e)}")

    return StreamingResponse(sse_producers(), media_type="text/event-stream")

# --- 5. 启动服务 ---
if __name__ == "__main__":
    import uvicorn
    # 建议使用 uvicorn 运行
    uvicorn.run(app, host="0.0.0.0", port=8000)