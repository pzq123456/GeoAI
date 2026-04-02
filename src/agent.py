import os
import json
from typing import Union, List, Optional
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.deepseek import DeepSeekProvider
from shapely.geometry import shape, mapping, LineString, Polygon
from shapely.ops import transform

from .schema import GISDependencies, GISAnalysisOutput, ClarificationResponse

# --- 模型配置 ---
model = OpenAIChatModel(
    model_name='deepseek-chat',
    provider=DeepSeekProvider(api_key=os.getenv('DEEPSEEK_API_KEY') or ""),
)

# --- AI 专家指令 (System Prompt) ---
SYSTEM_INSTRUCTIONS = [
    "You are a Senior GIS Analyst. You operate by manipulating 'Layers' and 'Feature References'.",
    "CRITICAL PROTOCOL:",
    "1. DISCOVERY: Always use `list_layers` then `search_features` before analysis. Do NOT guess layer names.",
    "2. BACKEND COMPUTE: Geometric calculations (buffer, measure) happen on the backend using the 'id' you provide.",
    "3. NO ASSUMPTIONS: If a search result shows no coordinates, it is for token efficiency. The backend HAS the coordinates. Use the ID to trigger actions.",
    "4. VISUALIZATION: You MUST call `create_buffer_by_ref` or `add_to_map` to make features visible. Mention what is currently on the map in your final report.",
    "5. COORDINATES: All geometry sent to visual staging must be in EPSG:4326 (WGS84).",
    "6. MEASUREMENTS: Always include units (m, m², km) in your final report."
]

gis_expert = Agent(
    model=model,
    deps_type=GISDependencies,
    output_type=Union[GISAnalysisOutput, ClarificationResponse],
    instructions=SYSTEM_INSTRUCTIONS,
)

# --- 1. 数据发现工具 ---

@gis_expert.tool
async def list_layers(ctx: RunContext[GISDependencies]) -> List[str]:
    """列出当前数据目录下所有可用的图层（JSON文件名）。"""
    ctx.deps.add_status("🔍 正在扫描空间数据库...")
    return [f.stem for f in ctx.deps.loader.base_path.glob("*.json")]

@gis_expert.tool
async def search_features(
    ctx: RunContext[GISDependencies], 
    layer_name: str, 
    query: Optional[str] = None
) -> str:
    """
    检索图层内的要素。返回 ID 和属性摘要（不含坐标以节省 Token）。
    如果要素没有原生 ID，后端会生成一个 idx_ 开头的虚拟 ID。
    """
    ctx.deps.add_status(f"🛰️ 正在检索图层 [{layer_name}] 中的要素...")
    try:
        data = ctx.deps.loader.load_geojson(f"{layer_name}.json")
        results = []
        for i, f in enumerate(data.get('features', [])):
            props = f.get("properties", {})
            # 兼容性 ID 处理
            f_id = f.get("id") or props.get("@id") or f"idx_{i}"
            
            if query and query.lower() not in str(props).lower():
                continue
            
            results.append({
                "id": f_id,
                "name": props.get("name") or props.get("label") or "Unnamed",
                "geom_type": f.get("geometry", {}).get("type"),
                "props": {k: v for k, v in props.items() if len(str(v)) < 60}
            })
        return json.dumps(results[:25], ensure_ascii=False)
    except Exception as e:
        return f"检索失败: {str(e)}"

# --- 2. 几何分析工具 (基于后端引用) ---

@gis_expert.tool
async def create_buffer_by_ref(
    ctx: RunContext[GISDependencies], 
    layer_name: str, 
    feature_id: str, 
    radius_m: float,
    label: str
) -> str:
    """
    对指定 ID 的要素创建缓冲区。计算在后端通过原始坐标完成。
    结果会自动推送到地图的可视化区域。
    """
    ctx.deps.add_status(f"📏 正在为要素 {feature_id} 执行 {radius_m}m 缓冲区计算...")
    try:
        data = ctx.deps.loader.load_geojson(f"{layer_name}.json")
        # 寻找匹配要素
        target = None
        for i, f in enumerate(data['features']):
            curr_id = f.get("id") or f.get("properties", {}).get("@id") or f"idx_{i}"
            if str(curr_id) == str(feature_id):
                target = f
                break
        
        if not target:
            return f"错误：在图层 {layer_name} 中找不到 ID 为 {feature_id} 的要素。"

        # 几何转换与修复
        geom = shape(target['geometry'])
        if not geom.is_valid: geom = geom.buffer(0)
        
        tf_to_m = ctx.deps.loader.get_transformer(from_crs="EPSG:4326", to_crs="EPSG:3857")
        tf_to_deg = ctx.deps.loader.get_transformer(from_crs="EPSG:3857", to_crs="EPSG:4326")
        
        # 投影到平面计算缓冲区，再转回经纬度
        buffered_geom = transform(tf_to_deg, transform(tf_to_m, geom).buffer(radius_m))
        
        visual_feat = {
            "type": "Feature",
            "geometry": mapping(buffered_geom),
            "properties": {
                **target.get("properties", {}),
                "ai_label": label,
                "analysis_type": "buffer",
                "radius_m": radius_m
            }
        }
        
        # 推送到 staging 列表
        ctx.deps.visual_staging.append(visual_feat)
        return f"✅ 成功：{radius_m}m 缓冲区已生成并渲染，标签为 '{label}'。"
    except Exception as e:
        return f"缓冲区分析异常: {str(e)}"

@gis_expert.tool
async def universal_measure_by_ref(ctx: RunContext[GISDependencies], layer_name: str, feature_id: str) -> str:
    """
    测量工具：计算指定要素的面积、长度和重心。自动处理投影转换。
    """
    ctx.deps.add_status(f"📐 正在计算要素 {feature_id} 的物理指标...")
    try:
        data = ctx.deps.loader.load_geojson(f"{layer_name}.json")
        target = next((f for i, f in enumerate(data['features']) 
                       if str(f.get("id") or f.get("properties", {}).get("@id") or f"idx_{i}") == str(feature_id)), None)
        
        if not target: return "未找到要素。"

        geom = shape(target['geometry'])
        tf_to_m = ctx.deps.loader.get_transformer()
        geom_m = transform(tf_to_m, geom)
        
        results = [f"--- {feature_id} 测量报告 ---", f"几何类型: {geom.geom_type}"]
        if isinstance(geom_m, (Polygon, LineString)):
            results.append(f"周长/长度: {geom_m.length:.2f} 米")
        if isinstance(geom_m, Polygon):
            results.append(f"投影面积: {geom_m.area:.2f} 平方米 ({geom_m.area/10000:.4f} 公顷)")
            
        return "\n".join(results)
    except Exception as e:
        return f"测量失败: {str(e)}"

# --- 3. 可视化控制工具 ---

@gis_expert.tool
async def add_to_map(ctx: RunContext[GISDependencies], layer_name: str, feature_id: str, label: str) -> str:
    """将数据库中的原始要素直接推送到地图上显示。"""
    try:
        data = ctx.deps.loader.load_geojson(f"{layer_name}.json")
        target = next((f for i, f in enumerate(data['features']) 
                       if str(f.get("id") or f.get("properties", {}).get("@id") or f"idx_{i}") == str(feature_id)), None)
        if target:
            target["properties"]["ai_label"] = label
            ctx.deps.visual_staging.append(target)
            return f"✅ 已将 {feature_id} 添加到地图展示。"
        return "要素不存在。"
    except Exception as e:
        return str(e)

@gis_expert.tool
async def get_map_inventory(ctx: RunContext[GISDependencies]) -> str:
    """自检工具：查看当前地图渲染队列（visual_staging）中已经有哪些要素。"""
    if not ctx.deps.visual_staging:
        return "当前地图渲染队列为空。"
    names = [f["properties"].get("ai_label") or f["properties"].get("name") for f in ctx.deps.visual_staging]
    return f"当前地图已加载要素: {', '.join(filter(None, names))}"

@gis_expert.tool
async def clear_visual_staging(ctx: RunContext[GISDependencies]) -> str:
    """清空地图渲染队列。"""
    ctx.deps.visual_staging = []
    ctx.deps.add_status("🧹 已清空所有可视化图层。")
    return "地图已清空。"

@gis_expert.tool
async def find_nearby_features(
    ctx: RunContext[GISDependencies], 
    source_layer: str, 
    source_feature_id: str, 
    target_layer: str, 
    radius_m: float = 0
) -> str:
    """
    空间相交分析：找到 A 图层要素（或其缓冲区）范围内，属于 B 图层的要素。
    如果 radius_m > 0，则先对源要素建立缓冲区再进行检索。
    """
    ctx.deps.add_status(f"🛰️ 正在执行空间交叉检索：{source_layer} -> {target_layer}...")
    try:
        # 1. 加载源要素
        source_data = ctx.deps.loader.load_geojson(f"{source_layer}.json")
        source_f = next((f for i, f in enumerate(source_data['features']) 
                        if str(f.get("id") or f.get("properties", {}).get("@id") or f"idx_{i}") == str(source_feature_id)), None)
        
        if not source_f: return f"错误：找不到源要素 {source_feature_id}"

        # 2. 准备空间引擎 (使用投影坐标系以确保米级精度)
        tf_to_m = ctx.deps.loader.get_transformer()
        source_geom_m = transform(tf_to_m, shape(source_f['geometry']))
        
        # 如果指定了半径，则建立缓冲区
        if radius_m > 0:
            analysis_area_m = source_geom_m.buffer(radius_m)
            area_desc = f"{radius_m}米缓冲区"
        else:
            analysis_area_m = source_geom_m
            area_desc = "原始几何边界"

        # 3. 加载目标图层并过滤
        target_data = ctx.deps.loader.load_geojson(f"{target_layer}.json")
        hits = []
        
        for i, f in enumerate(target_data.get('features', [])):
            target_geom_m = transform(tf_to_m, shape(f['geometry']))
            if analysis_area_m.intersects(target_geom_m):
                props = f.get("properties", {})
                hits.append({
                    "id": f.get("id") or props.get("@id") or f"idx_{i}",
                    "name": props.get("name") or "Unnamed POI",
                    "type": props.get("amenity") or props.get("animal") or "POI"
                })
                # 自动推送到地图以便用户查看
                f["properties"]["ai_label"] = f"Detected_{target_layer}"
                ctx.deps.visual_staging.append(f)

        return json.dumps({
            "summary": f"分析完成。在 {source_feature_id} 的 {area_desc} 内共发现 {len(hits)} 个 {target_layer} 要素。",
            "matches": hits
        }, ensure_ascii=False)
        
    except Exception as e:
        return f"空间分析失败: {str(e)}"