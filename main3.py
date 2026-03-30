import os
import json
import asyncio
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Any, Union, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.deepseek import DeepSeekProvider

from shapely.geometry import shape, mapping
import pyproj
from shapely.ops import transform
import logfire

# 配置
logfire.configure(send_to_logfire='never')
logfire.instrument_pydantic_ai()
load_dotenv()

# --- 1. 数据模型与引擎依赖 ---

class GeoDataLoader:
    def __init__(self, base_dir: str = "data"):
        self.base_path = Path(__file__).parent / base_dir

    def load_geojson(self, filename: str) -> Dict[str, Any]:
        file_path = self.base_path / filename
        if not file_path.exists():
            raise FileNotFoundError(f"缺少数据文件: {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def get_transformer(from_crs="EPSG:4326", to_crs="EPSG:3857"):
        return pyproj.Transformer.from_crs(from_crs, to_crs, always_xy=True).transform

@dataclass
class GISDependencies:
    loader: GeoDataLoader
    render_path: str = "web_render.json"

class ClarificationResponse(BaseModel):
    guidance: str = Field(description="友好的引导话语")
    missing_fields: List[str] = Field(description="缺失的关键信息")
    suggestions: List[str] = Field(description="点击建议")

class GISAnalysisOutput(BaseModel):
    analysis_steps: List[str] = Field(description="分析链路")
    final_report: str = Field(description="专家级总结报告")
    visualization_status: str = Field(description="地图渲染状态说明")

# --- 2. 定义 Agent 与专家指令 ---

model = OpenAIChatModel(
    model_name='deepseek-chat',
    provider=DeepSeekProvider(api_key=os.getenv('DEEPSEEK_API_KEY')),
)

gis_expert = Agent(
    model=model,
    deps_type=GISDependencies,
    output_type=Union[GISAnalysisOutput, ClarificationResponse],
    instructions=[
        "你是一个 GIS 专家。你具备查看地块列表、执行空间分析、数学计算和可视化的能力。",
        "1. 意图确认：如果用户描述模糊（如'那个围栏'），必须先调用 list_available_features 获取所有地块列表并让用户确认 ID。",
        "2. 链式思考：计算面积占比时，先通过 get_proximity_data 获取 area_m2，然后自主进行数学运算。",
        "3. 数据匹配：如果用户提供的 ID 在列表中不存在，请调用 list_available_features 确认正确 ID 并告知用户。",
        "4. 可视化：分析完成后，调用 save_to_visualization_layer 固化结果。",
        "5. 语气：像真正的规划师一样思考，提供人类可读的深度见解。"
    ],
)

# --- 3. 稳定版工具箱 ---

@gis_expert.tool
async def list_available_features(ctx: RunContext[GISDependencies]) -> str:
    """列出 park.json 中所有可用的地理要素及其详细描述。"""
    try:
        data = ctx.deps.loader.load_geojson("park.json")
        summary = []
        for f in data.get('features', []):
            props = f.get("properties", {})
            # 兼容性 ID 提取：外层 id > @id > id
            f_id = f.get("id") or props.get("@id") or props.get("id")
            
            if not f_id:
                continue

            # 提取业务特征描述
            tags = {
                "名称": props.get("name") or props.get("name:zh"),
                "动物园属性": props.get("zoo"),
                "休闲属性": props.get("leisure"),
                "设施": props.get("amenity")
            }
            desc_str = ", ".join([f"{k}:{v}" for k, v in tags.items() if v]) or "无详细标签"
            
            summary.append(f"- ID: {f_id} (描述: {desc_str})")
        
        if not summary:
            return "数据库中没有任何地理要素。"
        
        # 排序便于 AI 检索
        summary.sort()
        return "当前数据库中的可用地块列表如下：\n" + "\n".join(summary)
    except Exception as e:
        return f"获取列表失败: {str(e)}"

@gis_expert.tool
async def perform_math_calculation(ctx: RunContext[GISDependencies], expression: str) -> str:
    """数学计算工具。"""
    try:
        result = eval(expression, {"__builtins__": None}, {})
        return f"数学计算结果: {result}"
    except Exception as e:
        return f"计算失败: {str(e)}"

@gis_expert.tool
async def get_proximity_data(
    ctx: RunContext[GISDependencies], 
    target_id: str, 
    radius: float, 
    category: str
) -> Dict[str, Any]:
    """获取指定地块的面积及周边 POI。"""
    try:
        park_data = ctx.deps.loader.load_geojson("park.json")
        poi_data = ctx.deps.loader.load_geojson("poi.json")
        
        to_meters = ctx.deps.loader.get_transformer()
        to_degrees = ctx.deps.loader.get_transformer("EPSG:3857", "EPSG:4326")
        
        # 增强 ID 匹配：去除潜在的空格，并检查多个 ID 字段
        tid = str(target_id).strip()
        target_f = None
        for f in park_data['features']:
            props = f.get("properties", {})
            curr_id = f.get("id") or props.get("@id") or props.get("id")
            if str(curr_id).strip() == tid:
                target_f = f
                break

        if not target_f:
            return {"error": f"找不到 ID 为 {target_id} 的要素。"}

        geom_meters = transform(to_meters, shape(target_f['geometry']))
        buffer_poly = geom_meters.buffer(radius)
        buffer_wgs = transform(to_degrees, buffer_poly)
        
        selected_pois = [
            p for p in poi_data['features'] 
            if p['properties'].get('category') == category and 
            transform(to_meters, shape(p['geometry'])).within(buffer_poly)
        ]

        return {
            "area_m2": round(geom_meters.area, 2),
            "poi_count": len(selected_pois),
            "visual_packet": {
                "type": "FeatureCollection",
                "features": [
                    {**target_f, "properties": {**target_f.get("properties", {}), "layer": "target", "id": tid}},
                    {"type": "Feature", "properties": {"layer": "buffer"}, "geometry": mapping(buffer_wgs)},
                    *[{**p, "properties": {**p['properties'], "layer": "hits"}} for p in selected_pois]
                ]
            }
        }
    except Exception as e:
        return {"error": str(e)}

@gis_expert.tool
async def save_to_visualization_layer(ctx: RunContext[GISDependencies], geojson_data: Dict[str, Any]) -> str:
    """写入 web_render.json 供前端渲染。"""
    try:
        with open(ctx.deps.render_path, "w", encoding="utf-8") as f:
            json.dump(geojson_data, f, indent=2, ensure_ascii=False)
        return f"✅ 可视化数据已更新至 {ctx.deps.render_path}"
    except Exception as e:
        return f"❌ 渲染失败: {str(e)}"

# --- 4. 运行控制台 ---

async def main():
    # 确保数据目录存在
    Path("data").mkdir(exist_ok=True)
    
    deps = GISDependencies(loader=GeoDataLoader())
    history = []
    
    test_queries = [
        "那个动物园围栏面积多大？帮我算算它占 1000 平米的百分之几？",
        "分析 way/580279358 这个地块周边 20 米的 mammals 动物。"
    ]

    print("🛰️ GIS 专家系统启动（增强匹配模式）...\n")

    for q in test_queries:
        print(f"👤 用户: {q}")
        result = await gis_expert.run(q, deps=deps, message_history=history)
        history = result.new_messages()
        
        if isinstance(result.output, ClarificationResponse):
            print(f"🤖 引导: {result.output.guidance}")
            print(f"💡 建议: {result.output.suggestions}")
        else:
            print(f"✅ 专家报告: \n{result.output.final_report}")
            print(f"🌐 渲染状态: {result.output.visualization_status}")
        print("-" * 50)

if __name__ == "__main__":
    asyncio.run(main())