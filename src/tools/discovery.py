import json
import re
from typing import List, Dict, Any, Optional
from pydantic_ai import RunContext
from rapidfuzz import process, fuzz, utils
from ..utils.logger import logger
from ..schema import GISDependencies
from ..utils.geo_ops import (
    generate_stable_id, 
    find_best_name, 
    get_property_schema
)

async def list_layers(ctx: RunContext[GISDependencies]) -> List[str]:
    """列出系统中所有可用的 GIS 图层。"""
    ctx.deps.add_status("Scanning layers...")
    layers = [f.stem for f in ctx.deps.loader.base_path.glob("*.json")]
    logger.debug(f"已列出所有图层: {layers}")
    return layers

async def query_layer_features(
    ctx: RunContext[GISDependencies],
    layer_name: str,
    query: Optional[str] = None,
    criteria: Optional[Dict[str, Any]] = None,
    limit: int = 15
) -> str:
    """
    【综合检索工具】用于定位要素。
    - query: 自然语言关键词（如名称、地址、邮编）。
    - criteria: 属性精确过滤（如 {"Trust Name": "Trinity"}）。
    - 如果检索不到，工具会返回诊断信息及建议的属性键值。
    """
    ctx.deps.add_status(f"🔍 检索 [{layer_name}]: '{query or ''}'...")
    logger.info(f"综合检索: 图层={layer_name}, query='{query}', criteria={criteria}")

    try:
        data = ctx.deps.loader.load_geojson(f"{layer_name}.json")
        features = data.get('features', [])
        
        # --- 步骤 1: 属性过滤与参数清洗 ---
        filtered_pool = []
        if criteria:
            # 自动清洗 AI 误传的 MongoDB 风格正则参数
            cleaned_criteria = {}
            for k, v in criteria.items():
                if isinstance(v, dict): # 处理 {"$regex": "xxx"}
                    cleaned_criteria[k] = str(next(iter(v.values()))).replace(".*", "").lower()
                else:
                    cleaned_criteria[k] = str(v).lower()

            for i, f in enumerate(features):
                props = f.get("properties", {})
                match = True
                for k, target in cleaned_criteria.items():
                    actual = str(props.get(k, "")).lower()
                    if target not in actual:
                        match = False
                        break
                if match:
                    filtered_pool.append((i, f))
        else:
            filtered_pool = list(enumerate(features))

        # --- 步骤 2: 模糊评分与降级匹配 ---
        final_selection = []
        if query and filtered_pool:
            # 构建搜索文本池
            search_choices = []
            for _, f in filtered_pool:
                p = f.get("properties", {})
                # 权重：名称 > 邮编 > 地址
                text = f"{find_best_name(p)} {p.get('Postcode', '')} {p.get('Address 1', '')}"
                search_choices.append(utils.default_process(text))
            
            # 使用 token_set_ratio 处理部分包含关系（比 WRatio 容错更高）
            processed_query = utils.default_process(query)
            matches = process.extract(
                processed_query, 
                search_choices, 
                scorer=fuzz.token_set_ratio, 
                limit=limit
            )
            
            # 过滤掉评分过低的结果（阈值 50），但保留前 3 个作为“可能项”
            final_selection = [
                (filtered_pool[idx][0], filtered_pool[idx][1], score) 
                for _, score, idx in matches if score >= 50
            ]
        else:
            final_selection = [(idx, f, 100.0) for idx, f in filtered_pool[:limit]]

        # --- 步骤 3: 诊断报告（核心防空转逻辑） ---
        if not final_selection:
            schema = get_property_schema(data)
            diagnostic = {
                "status": "NOT_FOUND",
                "message": f"在图层 '{layer_name}' 中未找到匹配项。",
                "hint": "请检查字段名或尝试缩减关键词。",
                "available_properties_guide": schema,
                "note": "严禁使用复杂的正则语法，直接输入纯文本即可。"
            }
            # 如果有接近但不达标的项，给个暗示
            if query and filtered_pool:
                raw_top = process.extract(processed_query, search_choices, limit=2) # type: ignore
                diagnostic["did_you_mean"] = [find_best_name(filtered_pool[idx][1]["properties"]) for _, _, idx in raw_top]
            
            return json.dumps(diagnostic, ensure_ascii=False)

        # --- 步骤 4: 结果输出 ---
        results = []
        for i, f, score in final_selection:
            props = f.get("properties", {})
            results.append({
                "id": generate_stable_id(layer_name, f, i),
                "name": find_best_name(props),
                "match_score": f"{round(score, 1)}%",
                "key_props": {k: v for k, v in props.items() if k.lower() not in ['shape_area', 'shape_leng']}
            })

        logger.success(f"检索完成，找到 {len(results)} 条记录")
        return json.dumps({"status": "SUCCESS", "count": len(results), "data": results}, ensure_ascii=False)

    except Exception as e:
        logger.exception("综合检索过程异常")
        return json.dumps({"status": "ERROR", "message": str(e)})