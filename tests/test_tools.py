import json

from src.tools import discovery, analysis, visualization
from src.utils.geo_ops import generate_stable_id


async def test_list_layers(ctx):
    assert await discovery.list_layers(ctx) == ["tree"]


async def test_query_layer_features_success(ctx):
    result = json.loads(await discovery.query_layer_features(ctx, "tree", query="T03562"))
    assert result["status"] == "SUCCESS"
    assert result["count"] > 0
    assert result["data"][0]["id"] == "tree:1"


async def test_query_layer_features_not_found_has_diagnostics(ctx):
    result = json.loads(
        await discovery.query_layer_features(ctx, "tree", query="ZZZ_NOT_EXIST_XYZ")
    )
    assert result["status"] == "NOT_FOUND"
    assert "available_properties_guide" in result
    assert "did_you_mean" in result


async def test_query_layer_features_cleans_mongo_regex(ctx):
    result = json.loads(await discovery.query_layer_features(
        ctx, "tree", criteria={"code": {"$regex": "T03.*"}}
    ))
    assert result["status"] == "SUCCESS"
    assert result["count"] > 0


async def test_measure_tree_feature(ctx):
    report = await analysis.measure_tree_feature(ctx, "tree", "tree:1")
    assert "几何类型: Point" in report
    assert "WGS84" in report
    assert "没有面积或周长" in report


async def test_nearby_query_stages_visuals_without_mutating_source(ctx, deps):
    original = deps.loader.load_geojson("tree.json")["features"][0]
    assert "id" not in original

    result = json.loads(await analysis.spatial_query_nearby(
        ctx, "tree", "tree:1", "tree", radius_m=100, limit=10
    ))
    assert "summary" in result
    assert "spatial_data_table" in result
    assert any(
        f["properties"].get("analysis_type") == "buffer_zone"
        for f in deps.visual_staging
    )

    reloaded = deps.loader.load_geojson("tree.json")["features"][0]
    assert "id" not in reloaded  # source must not be mutated (replay determinism)


async def test_convex_hull(ctx, deps):
    search = json.loads(await discovery.query_layer_features(ctx, "tree", query="T03562"))
    ids = [item["id"] for item in search["data"][:5]]
    result = json.loads(await analysis.calculate_group_convex_hull(ctx, "tree", ids))
    assert result["status"] == "success"
    assert result["area_km2"] >= 0
    assert any(
        f["properties"].get("analysis_type") == "convex_hull"
        for f in deps.visual_staging
    )


async def test_distribution_balance_requires_four_points(ctx):
    result = await analysis.analyze_tree_distribution_balance(
        ctx, "tree", ["tree:1", "tree:2"]
    )
    assert "点集数量不足" in result


async def test_visualization_staging_lifecycle(ctx, deps):
    added = await visualization.add_to_map(ctx, "tree", "tree:1", "测试树")
    assert "成功" in added
    assert len(deps.visual_staging) == 1

    inventory = await visualization.get_map_inventory(ctx)
    assert "测试树" in inventory

    await visualization.clear_visual_staging(ctx)
    assert deps.visual_staging == []


async def test_invalid_layer_name_is_rejected_by_tools(ctx):
    result = await visualization.add_to_map(ctx, "../secret", "x", "y")
    assert "出错" in result or "找不到" in result
