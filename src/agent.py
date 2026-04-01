import os
from typing import Union, Dict, Any, List
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.deepseek import DeepSeekProvider
from shapely.geometry import shape, mapping, Point, LineString, Polygon, GeometryCollection
from shapely.ops import transform, unary_union

from .schema import GISDependencies, GISAnalysisOutput, ClarificationResponse
import math
from itertools import combinations

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
        "【严格渲染规则】调用 save_to_visualization_layer 时，必须使用 EPSG:4326 (经纬度) 坐标。",
        "【几何完整性】严禁将 Polygon 简化为 Point 发送给渲染层，除非用户明确要求显示重心。",
        "如果 universal_measure 返回面积为 0 且类型为 Polygon，说明数据退化，请在报告中提示用户数据质量问题。",
        "在分析多个地块时，优先使用 extract_context_structure 获取群体布局特征。",
        "所有数值输出必须带上单位（如：米、平方米、公里）。"
    ],
)

@gis_expert.tool
async def list_available_features(ctx: RunContext[GISDependencies]) -> str:
    """列出当前数据库中可用的地理要素 ID。"""
    ctx.deps.add_status("正在检索地块数据库...")
    try:
        data = ctx.deps.loader.load_geojson("park.json")
        ids = [f.get("id") or f.get("properties", {}).get("@id") for f in data.get('features', [])]
        return f"可用要素 ID 列表: {', '.join(filter(None, ids))}"
    except Exception as e:
        return f"检索失败: {str(e)}"

@gis_expert.tool
async def universal_measure(ctx: RunContext[GISDependencies], feature_id: str) -> str:
    """全面几何测量工具：计算面积、长度、周长。自动修复拓扑错误并返回几何类型。"""
    try:
        data = ctx.deps.loader.load_geojson("park.json")
        feat = next((f for f in data['features'] if (f.get("id") or f.get("properties", {}).get("@id")) == feature_id), None)
        if not feat: return f"错误：未找到 ID {feature_id}"

        geom = shape(feat['geometry'])
        if not geom.is_valid: geom = geom.buffer(0) # 自动修复自相交等拓扑错误
        
        # 转换到投影坐标系（米）进行物理计算
        tf_to_m = ctx.deps.loader.get_transformer()
        geom_m = transform(tf_to_m, geom)
        
        report = [f"--- 要素 {feature_id} 属性分析 ---", f"类型: {geom.geom_type}"]
        if isinstance(geom_m, (Polygon, LineString)):
            report.append(f"周长/长度: {geom_m.length:.2f} 米")
        if isinstance(geom_m, Polygon):
            report.append(f"投影面积: {geom_m.area:.2f} 平方米")
            if geom_m.area < 0.1: report.append("⚠️ 警告: 该多边形几乎没有面积，可能存在坐标重复。")
        
        c = geom_m.centroid
        report.append(f"几何重心 (本地坐标): {c.x:.2f}, {c.y:.2f}")
        return "\n".join(report)
    except Exception as e:
        return f"测量失败: {str(e)}"

@gis_expert.tool
async def extract_context_structure(ctx: RunContext[GISDependencies], feature_ids: List[str]) -> str:
    """
    空间结构提取：一次性计算多个要素之间的群体拓扑关系、距离矩阵和排列特征。
    """
    ctx.deps.add_status(f"正在构建 {len(feature_ids)} 个要素的空间拓扑网络...")
    try:
        data = ctx.deps.loader.load_geojson("park.json")
        targets = [f for f in data['features'] if (f.get("id") or f.get("properties", {}).get("@id")) in feature_ids]
        
        if len(targets) < 2: return "分析失败：要素数量不足，无法构成空间布局。"

        tf_to_m = ctx.deps.loader.get_transformer()
        geoms_m = [transform(tf_to_m, shape(t['geometry'])) for t in targets]
        
        # 1. 距离矩阵计算
        matrix = []
        for i in range(len(geoms_m)):
            for j in range(i + 1, len(geoms_m)):
                d = geoms_m[i].distance(geoms_m[j])
                matrix.append(f"[{feature_ids[i]}]至[{feature_ids[j]}]: {d:.2f}米")
        
        # 2. 宏观格局分析
        union_geom = unary_union(geoms_m)
        env = union_geom.envelope
        bounds = union_geom.bounds # minx, miny, maxx, maxy
        
        width, height = bounds[2] - bounds[0], bounds[3] - bounds[1]
        pattern = "南北纵向" if height > width else "东西横向"
        
        return (f"群体布局分析完成：\n"
                f"- 排列模式：整体呈现 {pattern} 分布。\n"
                f"- 间距细节：{'; '.join(matrix)}\n"
                f"- 总包络面积：{env.area:.2f} 平方米。\n"
                f"- 集群离散度：{'紧凑' if (union_geom.area / env.area) > 0.5 else '松散'}。")
    except Exception as e:
        return f"布局分析失败: {str(e)}"

@gis_expert.tool
async def get_proximity_data(ctx: RunContext[GISDependencies], target_id: str, radius: float) -> str:
    """执行缓冲区分析并检索覆盖范围内的 POI 点数据。"""
    ctx.deps.add_status(f"正在对 {target_id} 进行 {radius}米 半径的邻近性检索...")
    try:
        park_data = ctx.deps.loader.load_geojson("park.json")
        poi_data = ctx.deps.loader.load_geojson("poi.json")
        
        tf_to_m = ctx.deps.loader.get_transformer()
        tf_to_deg = ctx.deps.loader.get_transformer("EPSG:3857", "EPSG:4326")
        
        target_f = next((f for f in park_data['features'] if (f.get("id") or f.get("properties", {}).get("@id")) == target_id), None)
        if not target_f: return f"错误：未找到目标要素 {target_id}"

        geom_m = transform(tf_to_m, shape(target_f['geometry']))
        buffer_m = geom_m.buffer(radius)
        
        # 空间过滤
        hits = [p for p in poi_data['features'] if transform(tf_to_m, shape(p['geometry'])).intersects(buffer_m)]
        
        # 转换 buffer 为经纬度以便渲染
        buffer_geojson = mapping(transform(tf_to_deg, buffer_m))
        
        ctx.deps.visual_buffer = {
            "type": "FeatureCollection",
            "features": [
                {"type": "Feature", "geometry": buffer_geojson, "properties": {"layer": "buffer_zone", "ref": target_id}},
                *hits
            ]
        }
        
        return f"邻近性分析结果：在 {radius}米 范围内共发现 {len(hits)} 个关联兴趣点。结果已推送到渲染层。"
    except Exception as e:
        return f"邻近性分析异常: {str(e)}"

@gis_expert.tool
async def save_to_visualization_layer(ctx: RunContext[GISDependencies], geojson_data: Dict[str, Any]) -> str:
    """
    渲染层同步工具：将分析生成的地理结果保存到前端显示缓冲区。
    注意：传入的数据必须是 WGS84 (EPSG:4326) 坐标系。
    """
    # 简单的坐标合法性检查（防止模型错误发送投影坐标）
    try:
        first_feat = geojson_data.get('features', [{}])[0]
        coord_sample = str(first_feat.get('geometry', {}).get('coordinates', ''))
        if "12707" in coord_sample or "2544" in coord_sample:
            return "❌ 拒绝保存：检测到坐标数值过大，疑似为投影坐标（米）。请先转回经纬度(EPSG:4326)再保存。"
    except:
        pass

    ctx.deps.visual_buffer = geojson_data
    ctx.deps.add_status("可视化数据同步完成，准备渲染...")
    return "✅ 渲染层同步成功"

@gis_expert.tool
async def analyze_topological_relationships(ctx: RunContext[GISDependencies], feature_ids: List[str]) -> str:
    """
    拓扑关系诊断：识别要素间的空间交互（相接、包含、交叉）。
    可视化：高亮显示具有拓扑关联的要素对。
    """
    ctx.deps.add_status("正在构建拓扑关系矩阵...")
    try:
        data = ctx.deps.loader.load_geojson("park.json")
        tf_to_deg = ctx.deps.loader.get_transformer("EPSG:3857", "EPSG:4326")
        
        targets = [f for f in data['features'] if (f.get("id") or f.get("properties", {}).get("@id")) in feature_ids]
        results = []
        visual_features = []

        for f1, f2 in combinations(targets, 2):
            g1, g2 = shape(f1['geometry']), shape(f2['geometry'])
            id1, id2 = f1.get("id", "f1"), f2.get("id", "f2")
            
            rel = "disjoint"
            if g1.touches(g2): rel = "TOUCH (相邻/挂接)"
            elif g1.contains(g2): rel = f"CONTAINS ({id1} 包含 {id2})"
            elif g2.contains(g1): rel = f"WITHIN ({id1} 在 {id2} 内)"
            elif g1.intersects(g2): rel = "INTERSECT (重叠/交叉)"
            
            if rel != "disjoint":
                results.append(f"[{id1}] <-> [{id2}]: {rel}")
                # 提取关联部分进行可视化
                visual_features.append(f1)
                visual_features.append(f2)

        if not results: return "分析完成：所选要素在空间上完全独立，无直接拓扑接触。"

        ctx.deps.visual_buffer = {"type": "FeatureCollection", "features": visual_features}
        return "发现以下拓扑关系：\n" + "\n".join(results) + "\n✅ 关联要素已推送到渲染层。"
    except Exception as e:
        return f"拓扑分析失败: {str(e)}"

@gis_expert.tool
async def calculate_spatial_clustering(ctx: RunContext[GISDependencies], feature_ids: List[str]) -> str:
    """
    空间聚集度分析：使用 ANN (平均最近邻) 算法判断分布模式。
    可视化：生成所有要素的凸包 (Convex Hull) 及其重心点。
    """
    ctx.deps.add_status("计算空间分布显著性...")
    try:
        data = ctx.deps.loader.load_geojson("park.json")
        tf_to_m = ctx.deps.loader.get_transformer()
        tf_to_deg = ctx.deps.loader.get_transformer("EPSG:3857", "EPSG:4326")
        
        geoms_m = [transform(tf_to_m, shape(f['geometry'])) for f in data['features'] if (f.get("id") or f.get("properties", {}).get("@id")) in feature_ids]
        centroids = [g.centroid for g in geoms_m]
        
        # ANN 计算
        n = len(centroids)
        if n < 3: return "样本量过小，无法进行聚集度统计。"
        
        sum_dist = 0
        for i, p1 in enumerate(centroids):
            min_d = min(p1.distance(p2) for j, p2 in enumerate(centroids) if i != j)
            sum_dist += min_d
        
        obs_avg_dist = sum_dist / n
        # 理论随机距离: 0.5 / sqrt(n/Area)
        area = unary_union(geoms_m).envelope.area
        exp_avg_dist = 0.5 / math.sqrt(n / area) if area > 0 else 1
        r_value = obs_avg_dist / exp_avg_dist
        
        status = "聚集 (Clustered)" if r_value < 1 else "离散 (Dispersed)"
        if 0.9 < r_value < 1.1: status = "随机 (Random)"

        # 可视化：生成凸包
        hull_m = unary_union(geoms_m).convex_hull
        hull_geo = mapping(transform(tf_to_deg, hull_m))
        
        ctx.deps.visual_buffer = {
            "type": "FeatureCollection",
            "features": [
                {"type": "Feature", "geometry": hull_geo, "properties": {"label": "聚集范围凸包", "r_index": round(r_value, 2)}},
                *[{"type": "Feature", "geometry": mapping(transform(tf_to_deg, c)), "properties": {"type": "centroid"}} for c in centroids]
            ]
        }
        
        return f"分布模式：{status}\n- ANN 指数: {r_value:.2f}\n- 观测平均距离: {obs_avg_dist:.2f} 米\n✅ 聚集凸包与重心已推送渲染。"
    except Exception as e:
        return f"聚集分析异常: {str(e)}"

@gis_expert.tool
async def analyze_network_centrality(ctx: RunContext[GISDependencies], line_ids: List[str]) -> str:
    """
    线网络中心性分析：识别路网/线状要素中的关键枢纽。
    可视化：将线段按重要程度进行分级渲染（模拟热力效果）。
    """
    ctx.deps.add_status("正在构建逻辑路网结构...")
    try:
        data = ctx.deps.loader.load_geojson("park.json")
        tf_to_deg = ctx.deps.loader.get_transformer("EPSG:3857", "EPSG:4326")
        
        lines = [f for f in data['features'] if (f.get("id") or f.get("properties", {}).get("@id")) in line_ids]
        if not lines: return "未找到有效的线状要素进行网络分析。"

        # 简化版中心性逻辑：计算每条线与其他线的连接数 (Degree)
        line_geoms = [(f, shape(f['geometry'])) for f in lines]
        connectivity = []
        
        for i, (f1, g1) in enumerate(line_geoms):
            connections = 0
            for j, (f2, g2) in enumerate(line_geoms):
                if i != j and g1.intersects(g2):
                    connections += 1
            
            # 将连接度存入属性
            f1_copy = f1.copy()
            f1_copy['properties'] = {**f1.get('properties', {}), "connectivity": connections, "weight": connections * 2}
            connectivity.append((f1.get("id"), connections, f1_copy))

        # 按重要性排序
        connectivity.sort(key=lambda x: x[1], reverse=True)
        top_node = connectivity[0]
        
        ctx.deps.visual_buffer = {
            "type": "FeatureCollection",
            "features": [item[2] for item in connectivity]
        }

        return (f"网络分析完成：\n"
                f"- 核心节点：{top_node[0]} (连接数: {top_node[1]})\n"
                f"- 网络连通性已在渲染层通过 'connectivity' 权重进行分级显示。")
    except Exception as e:
        return f"路网分析失败: {str(e)}"