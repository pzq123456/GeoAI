import os
import json
import asyncio
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.deepseek import DeepSeekProvider

from shapely.geometry import shape, Point, Polygon, mapping
import pyproj
from shapely.ops import transform
import logfire

logfire.configure(send_to_logfire='never')
logfire.instrument_pydantic_ai()
load_dotenv()

# --- 1. 专业数据加载与转换器 ---
class GeoDataLoader:
    def __init__(self, base_dir: str = "data"):
        self.base_path = Path(__file__).parent / base_dir

    def load_geojson(self, filename: str) -> Dict[str, Any]:
        file_path = self.base_path / filename
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def get_transformer(from_crs="EPSG:4326", to_crs="EPSG:3857"):
        return pyproj.Transformer.from_crs(from_crs, to_crs, always_xy=True).transform

@dataclass
class GISDependencies:
    loader: GeoDataLoader

# 结构化输出：增加 map_features 用于存放前端渲染所需的 GeoJSON
class GISAnalysisOutput(BaseModel):
    analysis_steps: List[str] = Field(description="详细的 GIS 空间分析步骤")
    result_details: Dict[str, Any] = Field(description="分析得出的量化结果数据")
    map_features: Dict[str, Any] = Field(description="用于前端地图渲染的 GeoJSON 要素集")
    final_report: str = Field(description="基于空间拓扑关系的专业结论报告")

# --- 2. 定义 Agent ---
model = OpenAIChatModel(
    model_name='deepseek-chat',
    provider=DeepSeekProvider(api_key=os.getenv('DEEPSEEK_API_KEY')),
)

gis_expert = Agent(
    model=model,
    deps_type=GISDependencies,
    output_type=GISAnalysisOutput,
    instructions=(
        '你是一个资深 GIS 空间规划专家。'
        '你擅长处理空间拓扑关系并为前端提供可视化数据。'
        '当用户要求分析时，你必须调用工具获取数据，并确保 map_features 中包含：'
        '1. 原始要素 2. 缓冲区要素 3. 被选中的 POI 要素。'
    ),
)

# --- 3. 注册支持可视化数据生成的工具 ---

@gis_expert.tool
async def perform_proximity_analysis(
    ctx: RunContext[GISDependencies], 
    target_feature_id: str, 
    buffer_meters: float, 
    poi_category: str
) -> Dict[str, Any]:
    """
    邻域分析并返回可视化要素：包含面积计算、缓冲区生成及 POI 拓扑筛选。
    """
    try:
        park_data = ctx.deps.loader.load_geojson("park.json")
        poi_data = ctx.deps.loader.load_geojson("poi.json")
        
        to_meters = ctx.deps.loader.get_transformer("EPSG:4326", "EPSG:3857")
        to_degrees = ctx.deps.loader.get_transformer("EPSG:3857", "EPSG:4326")
        
        target_f = next((f for f in park_data['features'] if f.get("id") == target_feature_id or f.get("properties", {}).get("id") == target_feature_id), None)
        if not target_f:
            return {"error": f"未找到地块 {target_feature_id}"}

        # 计算与缓冲区生成
        geom_meters = transform(to_meters, shape(target_f['geometry']))
        buffer_meters_geom = geom_meters.buffer(buffer_meters)
        
        # 将缓冲区转回经纬度供前端渲染
        buffer_wgs84 = transform(to_degrees, buffer_meters_geom)
        
        # 拓扑筛选
        selected_poi_features = []
        for f in poi_data['features']:
            if f['properties'].get('category') == poi_category:
                p_geom_meters = transform(to_meters, shape(f['geometry']))
                if p_geom_meters.within(buffer_meters_geom):
                    selected_poi_features.append(f)

        # 构建前端渲染合集
        render_collection = {
            "type": "FeatureCollection",
            "features": [
                {**target_f, "properties": {**target_f.get("properties", {}), "layer": "original"}},
                {
                    "type": "Feature",
                    "properties": {"layer": "buffer", "radius": buffer_meters},
                    "geometry": mapping(buffer_wgs84)
                },
                *[{**f, "properties": {**f.get("properties", {}), "layer": "selected_poi"}} for f in selected_poi_features]
            ]
        }
        
        return {
            "area_m2": round(geom_meters.area, 2),
            "poi_count": len(selected_poi_features),
            "geojson": render_collection
        }
        
    except Exception as e:
        return {"error": str(e)}

# --- 4. 运行 ---
async def main():
    deps = GISDependencies(loader=GeoDataLoader(base_dir="data"))
    query = "分析 way/580279358 地块及周边 20 米的 mammals POI，并返回可视化数据。"
    
    result = await gis_expert.run(query, deps=deps)
    output = result.output

    print("--- 🗺️ 可视化数据准备就绪 ---")
    print(f"📊 统计数据: {output.result_details}")
    
    # 这里模拟前端拿到的数据
    features = output.map_features.get("features", [])
    print(f"🎨 待渲染要素数量: {len(features)}")
    for f in features:
        print(f"  - [图层: {f['properties'].get('layer')}] 类型: {f['geometry']['type']}")

    print(f"\n🏛️ 专家报告: \n{output.final_report}")

    # 你可以将 output.map_features 保存为文件，直接拖进 geojson.io 查看
    with open("result_render.json", "w") as f:
        json.dump(output.map_features, f)
    print("\n✅ 结果已保存至 result_render.json，可直接在地图中查看。")

if __name__ == '__main__':
    asyncio.run(main())