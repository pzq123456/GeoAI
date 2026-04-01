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

# --- 0. 路径与环境配置 (最佳实践) ---

# 获取项目根目录：src/main.py -> parent(src) -> parent(project_root)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"

# 自动创建必要目录
DATA_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# 加载 .env（显式指定路径防止在 src 内运行加载失败）
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

# 日志配置
logfire.configure(send_to_logfire='never')
logfire.instrument_pydantic_ai()

# --- 1. 数据模型与引擎依赖 ---

class GeoDataLoader:
    """具备路径自适应能力的数据加载类"""
    def __init__(self, base_dir: Path = DATA_DIR):
        self.base_path = base_dir

    def load_geojson(self, filename: str) -> Dict[str, Any]:
        file_path = self.base_path / filename
        if not file_path.exists():
            # 报错时输出绝对路径，方便 Debug
            raise FileNotFoundError(f"缺少数据文件: {file_path.absolute()}")
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def get_transformer(from_crs="EPSG:4326", to_crs="EPSG:3857"):
        return pyproj.Transformer.from_crs(from_crs, to_crs, always_xy=True).transform

@dataclass
class GISDependencies:
    loader: GeoDataLoader
    render_path: Path = OUTPUT_DIR / "web_render.json"

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
        "1. 意图确认：如果用户描述模糊，必须先调用 list_available_features 获取列表。",
        "2. 链式思考：计算面积占比时，先通过 get_proximity_data 获取 area_m2，然后自主进行数学运算。",
        "3. 数据匹配：如果 ID 不存在，请调用 list_available_features 确认正确 ID。",
        "4. 可视化：分析完成后，调用 save_to_visualization_layer 固化结果。",
        "5. 语气：像真正的规划师一样思考，提供人类可读的深度见解。"
    ],
)

# --- 3. 稳定版工具箱 ---

@gis_expert.tool
async def list_available_features(ctx: RunContext[GISDependencies]) -> str:
    """列出所有可用的地理要素及其详细描述。"""
    try:
        data = ctx.deps.loader.load_geojson("park.json")
        summary = []
        for f in data.get('features', []):
            props = f.get("properties", {})
            f_id = f.get("id") or props.get("@id") or props.get("id")
            if not f_id: continue

            tags = {
                "名称": props.get("name") or props.get("name:zh"),
                "类型": props.get("zoo") or props.get("leisure") or props.get("amenity")
            }
            desc_str = ", ".join([f"{k}:{v}" for k, v in tags.items() if v]) or "无详细标签"
            summary.append(f"- ID: {f_id} (描述: {desc_str})")
        
        return "可用地块列表：\n" + "\n".join(sorted(summary)) if summary else "数据库为空。"
    except Exception as e:
        return f"获取列表失败: {str(e)}"

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
        
        tid = str(target_id).strip()
        target_f = next((f for f in park_data['features'] if str(f.get("id") or f.get("properties", {}).get("@id")) == tid), None)

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
                    {**target_f, "properties": {**target_f.get("properties", {}), "layer": "target"}},
                    {"type": "Feature", "properties": {"layer": "buffer"}, "geometry": mapping(buffer_wgs)},
                    *[{**p, "properties": {**p['properties'], "layer": "hits"}} for p in selected_pois]
                ]
            }
        }
    except Exception as e:
        return {"error": str(e)}

@gis_expert.tool
async def save_to_visualization_layer(ctx: RunContext[GISDependencies], geojson_data: Dict[str, Any]) -> str:
    """写入 JSON 供前端渲染。"""
    try:
        with open(ctx.deps.render_path, "w", encoding="utf-8") as f:
            json.dump(geojson_data, f, indent=2, ensure_ascii=False)
        return f"✅ 可视化数据已更新至 {ctx.deps.render_path.name}"
    except Exception as e:
        return f"❌ 渲染失败: {str(e)}"

# --- 4. 运行控制台 ---

async def main():
    # 实例化依赖
    loader = GeoDataLoader(DATA_DIR)
    deps = GISDependencies(loader=loader)
    
    print(f"🚀 系统就绪 | 根目录: {PROJECT_ROOT}")
    print(f"数据目录: {DATA_DIR.relative_to(PROJECT_ROOT)}")
    print("-" * 50)

    history = []
    test_queries = [
        "那个动物园围栏面积多大？帮我算算它占 1000 平米的百分之几？",
        "分析 way/580279358 这个地块周边 20 米的 mammals 动物。"
    ]

    for q in test_queries:
        print(f"👤 用户: {q}")
        result = await gis_expert.run(q, deps=deps, message_history=history)
        history = result.new_messages()
        
        if isinstance(result.output, ClarificationResponse):
            print(f"🤖 引导: {result.output.guidance}")
        else:
            print(f"✅ 专家报告: \n{result.output.final_report}")
            print(f"🌐 状态: {result.output.visualization_status}")
        print("-" * 50)

if __name__ == "__main__":
    asyncio.run(main())