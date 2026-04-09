import copy
from pydantic_ai import RunContext
from ..utils.logger import logger
from ..schema import GISDependencies
from ..utils.geo_ops import generate_stable_id

def _get_feature_by_ref(data: dict, layer_name: str, feature_id: str):
    for i, f in enumerate(data.get('features', [])):
        if generate_stable_id(layer_name, f, i) == feature_id:
            return f
    return None

async def add_to_map(ctx: RunContext[GISDependencies], layer_name: str, feature_id: str, label: str) -> str:
    ctx.deps.add_status(f"📍 正在尝试将要素 {feature_id} 标点到地图...")
    logger.info(f"地图上点请求: 图层={layer_name}, ID={feature_id}")
    try:
        data = ctx.deps.loader.load_geojson(f"{layer_name}.json")
        target = _get_feature_by_ref(data, layer_name, feature_id)
        
        if target:
            feat_to_render = copy.deepcopy(target)
            feat_to_render["properties"]["ai_label"] = label
            feat_to_render["id"] = feature_id 
            
            ctx.deps.visual_staging.append(feat_to_render)
            logger.success(f"要素 {feature_id} 已成功加入渲染队列")
            return f"✅ 已成功将 {label} (ID: {feature_id}) 添加到地图渲染队列。"
        
        logger.warning(f"无法在 {layer_name} 中找到 ID {feature_id}")
        return f"❌ 添加失败：在图层 {layer_name} 中找不到 ID 为 {feature_id} 的要素。"
    except Exception as e:
        logger.exception("地图上点执行出错")
        return f"🚨 添加出错: {str(e)}"

async def get_map_inventory(ctx: RunContext[GISDependencies]) -> str:
    logger.debug("执行地图库存自检")
    if not ctx.deps.visual_staging:
        return "当前地图为空。"
    names = [f["properties"].get("ai_label") or f["properties"].get("name") for f in ctx.deps.visual_staging]
    return f"当前地图已加载: {', '.join(filter(None, names))}"

async def clear_visual_staging(ctx: RunContext[GISDependencies]) -> str:
    ctx.deps.visual_staging = []
    ctx.deps.add_status("🧹 已清空所有可视化图层。")
    logger.info("已手动清空地图渲染队列")
    return "地图已清空。"