import copy
import json
from typing import List
from pydantic_ai import RunContext
from shapely.geometry import shape, mapping, Polygon, MultiPoint, Point
from shapely.ops import voronoi_diagram
# 导入我们统一的 logger
from ..utils.logger import logger
from ..schema import GISDependencies
from ..utils.geo_ops import (
    generate_stable_id,
    dehydrate_geojson,
    find_feature_by_id,
    to_metric,
    to_wgs84,
)

async def spatial_query_nearby(
    ctx: RunContext[GISDependencies], 
    source_layer: str, 
    source_feature_id: str, 
    target_layer: str, 
    radius_m: float = 0,
    visualize_buffer: bool = True,
    limit: int = 50
) -> str:
    log_context = f"[{source_layer} -> {target_layer} @ {radius_m}m]"
    ctx.deps.add_status(f"🔍 启动空间分析 {log_context}...")
    logger.info(f"开始空间邻近查询: {log_context}")
    
    try:
        src_data = ctx.deps.loader.load_geojson(f"{source_layer}.json")
        src_feat = find_feature_by_id(src_data, source_layer, source_feature_id)
        
        if not src_feat:
            msg = f"❌ 定位失败：图层 {source_layer} 中不存在 ID 为 {source_feature_id} 的要素"
            logger.error(msg)
            return msg

        src_geom = shape(src_feat['geometry'])
        if not src_geom.is_valid:
            logger.warning(f"{log_context}: 源几何无效，尝试 buffer(0) 修复")
            src_geom = src_geom.buffer(0)

        src_geom_m = to_metric(src_geom)
        logger.debug(f"{log_context}: 源要素投影面积 = {src_geom_m.area:.2f} m²")

        analysis_area_m = src_geom_m.buffer(radius_m) if radius_m > 0 else src_geom_m
        analysis_area_deg = to_wgs84(analysis_area_m)
        
        if visualize_buffer and radius_m > 0:
            ctx.deps.visual_staging.append({
                "type": "Feature",
                "geometry": mapping(analysis_area_deg),
                "properties": {
                    "ai_label": f"分析范围 ({radius_m}m)",
                    "analysis_type": "buffer_zone",
                    "source_ref": source_feature_id
                }
            })
            logger.debug(f"{log_context}: 已推送缓冲区可视化队列")

        target_data = ctx.deps.loader.load_geojson(f"{target_layer}.json")
        all_target_features = target_data.get('features', [])
        logger.debug(f"{log_context}: 目标图层加载成功，共 {len(all_target_features)} 个候选要素")

        hit_features = []
        for i, f in enumerate(all_target_features):
            t_geom = shape(f['geometry'])
            if analysis_area_deg.intersects(t_geom):
                # Never mutate the object returned by the loader: replaying the
                # same input must produce the same output.
                staged = copy.deepcopy(f)
                staged["id"] = generate_stable_id(target_layer, f, i)
                staged["properties"]["ai_label"] = f"Nearby_{target_layer}"
                ctx.deps.visual_staging.append(staged)
                hit_features.append(staged)

        logger.info(f"{log_context}: 检索完成，命中数量 = {len(hit_features)}")

        dehydrated = dehydrate_geojson(
            {"type": "FeatureCollection", "features": hit_features}, 
            target_layer, 
            limit=limit
        )

        result = {
            "summary": f"成功：在 {radius_m}m 范围内找到 {len(hit_features)} 个目标要素。",
            "spatial_data_table": dehydrated
        }
        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        logger.exception(f"空间分析过程崩溃: {log_context}")
        return f"🚨 空间分析崩溃 [{type(e).__name__}]: {str(e)}"

async def measure_tree_feature(ctx: RunContext[GISDependencies], layer_name: str, feature_id: str) -> str:
    """测量一棵树（或任意要素）的几何指标。注意：点要素只有坐标，没有面积/周长。"""
    ctx.deps.add_status(f"📐 正在测量要素 {feature_id}...")
    try:
        data = ctx.deps.loader.load_geojson(f"{layer_name}.json")
        target = find_feature_by_id(data, layer_name, feature_id)
        
        if not target:
            logger.error(f"测量失败: 在图层 {layer_name} 中找不到 ID {feature_id}")
            return "未找到要素。"

        geom = shape(target['geometry'])
        geom_m = to_metric(geom)

        logger.debug(f"要素 {feature_id} 投影完成，开始计算物理指标")

        res = [f"--- {feature_id} 测量报告 ---", f"几何类型: {geom.geom_type}"]
        if geom.geom_type == "Point":
            res.append(f"坐标 (WGS84): {geom.x:.6f}, {geom.y:.6f}")
            res.append("说明: 点要素没有面积或周长指标。")
        if geom_m.length:
            res.append(f"周长/长度: {geom_m.length:.2f} 米")
        if isinstance(geom, Polygon):
            res.append(f"投影面积: {geom_m.area:.2f} 平方米")
            
        return "\n".join(res)
    except Exception as e:
        logger.exception(f"测量工具执行失败: {feature_id}")
        return f"测量失败: {str(e)}"

async def calculate_group_convex_hull(
    ctx: RunContext[GISDependencies], 
    layer_name: str, 
    feature_ids: List[str],
    label: str = "要素聚集区域"
) -> str:
    """计算一组要素的包络范围（凸包）；密集点集的面积可能接近 0。"""
    ctx.deps.add_status(f"🛠️ 正在计算 {len(feature_ids)} 个要素的边界包络...")
    logger.info(f"开始计算凸包: {layer_name}, 要素数: {len(feature_ids)}")
    try:
        data = ctx.deps.loader.load_geojson(f"{layer_name}.json")
        points = []
        
        for fid in feature_ids:
            feat = find_feature_by_id(data, layer_name, fid)
            if feat:
                geom = shape(feat['geometry'])
                points.append(geom.centroid if not isinstance(geom, Point) else geom)

        if len(points) < 3:
            logger.warning(f"凸包计算中止: 有效点数 {len(points)} 不足 3 个")
            return "分析失败：计算凸包至少需要 3 个有效的地理坐标点。"

        multipoint = MultiPoint(points)
        hull_geom = multipoint.convex_hull

        hull_m = to_metric(hull_geom)
        area_km2 = hull_m.area / 1_000_000

        ctx.deps.visual_staging.append({
            "type": "Feature",
            "geometry": mapping(hull_geom),
            "properties": {
                "ai_label": label,
                "analysis_type": "convex_hull",
                "member_count": len(points),
                "area_km2": round(area_km2, 2)
            }
        })
        logger.success(f"凸包计算成功: 面积 {area_km2:.2f} km²")

        return json.dumps({
            "status": "success",
            "method": "Convex Hull",
            "area_km2": round(area_km2, 2),
            "summary": f"已生成覆盖 {len(points)} 个要素的凸包区域，面积约为 {area_km2:.2f} 平方公里。"
        }, ensure_ascii=False)

    except Exception as e:
        logger.exception("凸包分析过程中发生非预期错误")
        return f"分析过程中发生错误: {str(e)}"

async def analyze_tree_distribution_balance(
    ctx: RunContext[GISDependencies], 
    layer_name: str, 
    feature_ids: List[str]
) -> str:
    """
    【树群分布诊断】基于凸包约束的泰森多边形，评估一组树的分布均衡程度。
    结果中的“面积”指每棵树独占的维诺区域大小，而非设施服务覆盖。
    """
    ctx.deps.add_status("🧠 正在构建凸包约束下的空间模型...")
    
    try:
        # 1. 数量过滤与点集准备
        data = ctx.deps.loader.load_geojson(f"{layer_name}.json")
        points = []
        for fid in feature_ids:
            feat = find_feature_by_id(data, layer_name, fid)
            if feat:
                points.append(shape(feat['geometry']).centroid)

        if len(points) < 4: # 建议至少4个点，三角形的泰森多边形过于简单
            return "分析失败：点集数量不足（需至少4个点），无法构建有效的均衡度模型。"

        # 2. 计算凸包 (Hull) 作为约束边界
        multipoint = MultiPoint(points)
        hull_geom = multipoint.convex_hull
        
        # 3. 计算原始泰森多边形 (Voronoi)
        # 注意：voronoi_diagram 返回的是 GeometryCollection
        raw_voronoi = voronoi_diagram(multipoint)

        # 4. 空间裁剪 (Clipping)
        # 只保留凸包内部的部分
        clipped_cells = []
        for cell in raw_voronoi.geoms:
            intersection = cell.intersection(hull_geom)
            if not intersection.is_empty:
                clipped_cells.append(intersection)

        # 5. 投影与语义化指标计算
        areas_km2 = [(to_metric(c).area / 1_000_000) for c in clipped_cells]
        
        total_area = sum(areas_km2)
        avg_area = total_area / len(areas_km2)
        imbalance_ratio = max(areas_km2) / min(areas_km2) if min(areas_km2) > 0 else 0

        # 6. 语义解读：针对树木分布，而非设施服务覆盖
        if imbalance_ratio > 4:
            interpretation = "🚩 警告：该树群分布极不均衡，部分树木过于密集，另有明显空缺区域。"
        elif imbalance_ratio > 2:
            interpretation = "⚠️ 提示：树群分布存在中度失衡，边缘区域树木间距偏大。"
        else:
            interpretation = "✅ 结论：树群空间分布较均衡，间距合理。"

        # 7. 可视化渲染：同时推送约束边界和裁剪后的网格
        ctx.deps.visual_staging.append({
            "type": "Feature",
            "geometry": mapping(hull_geom),
            "properties": {"ai_label": "分析边界(凸包)", "fill": "none", "stroke": "#FF0000"}
        })
        for i, cell in enumerate(clipped_cells):
            ctx.deps.visual_staging.append({
                "type": "Feature",
                "geometry": mapping(cell),
                "properties": {
                    "ai_label": f"树群分布区_{i}",
                    "area_km2": round(areas_km2[i], 2)
                }
            })

        return json.dumps({
            "analysis_scope": "Convex Hull Constrained Voronoi",
            "metrics": {
                "total_area_km2": round(total_area, 2),
                "avg_service_area_km2": round(avg_area, 2),
                "imbalance_ratio": round(imbalance_ratio, 2)
            },
            "expert_conclusion": interpretation
        }, ensure_ascii=False)

    except Exception as e:
        logger.exception("空间约束分析崩溃")
        return f"🚨 分析崩溃: {str(e)}"