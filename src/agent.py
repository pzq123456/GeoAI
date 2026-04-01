# src/agent.py
import os
from typing import Union, Dict, Any
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.deepseek import DeepSeekProvider
from shapely.geometry import shape, mapping
from shapely.ops import transform

from .schema import GISDependencies, GISAnalysisOutput, ClarificationResponse

model = OpenAIChatModel(
    model_name='deepseek-chat',
    provider=DeepSeekProvider(api_key=os.getenv('DEEPSEEK_API_KEY') or ""),
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

@gis_expert.tool
async def list_available_features(ctx: RunContext[GISDependencies]) -> str:
    """列出 park.json 中可用的地理要素。"""
    ctx.deps.add_status("正在检索地块数据库...")
    try:
        data = ctx.deps.loader.load_geojson("park.json")
        features = data.get('features', [])
        ids = [f.get("id") or f.get("properties", {}).get("@id") for f in features]
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
        
        if not target_f:
            return {"error": f"未找到 ID 为 {target_id} 的要素"}

        geom_meters = transform(to_meters, shape(target_f['geometry']))
        buffer_poly = geom_meters.buffer(radius)
        buffer_wgs = transform(to_degrees, buffer_poly)
        
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
        return {"error": f"分析过程中出现异常: {str(e)}"}

@gis_expert.tool
async def save_to_visualization_layer(ctx: RunContext[GISDependencies], geojson_data: Dict[str, Any]) -> str:
    """将结果存入缓冲区供前端调用。"""
    ctx.deps.visual_buffer = geojson_data
    ctx.deps.add_status("空间可视化图层准备完毕。")
    return "✅ 数据已进入渲染缓冲区"