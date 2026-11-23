import pytest
from pydantic import ValidationError

from src.schema import ChatRequest, GeoDataLoader, GISDependencies, METRIC_CRS
from src.utils.geo_ops import generate_stable_id


def test_load_tree_dataset_and_normalize_coordinates():
    data = GeoDataLoader().load_geojson("tree.json")
    features = data["features"]
    assert len(features) == 2926
    assert data["type"] == "FeatureCollection"
    # Source data is 4D with a -1.8e308 sentinel; loader must trim to x/y.
    assert all(len(f["geometry"]["coordinates"]) == 2 for f in features)
    assert all(-180 <= f["geometry"]["coordinates"][0] <= 180 for f in features)
    assert all(-90 <= f["geometry"]["coordinates"][1] <= 90 for f in features)


def test_loader_rejects_unknown_layer_and_path_traversal():
    loader = GeoDataLoader()
    with pytest.raises(ValueError, match="Unknown layer"):
        loader.load_geojson("../../etc/passwd")
    with pytest.raises(ValueError, match="Unknown layer"):
        loader.load_geojson("schools.json")


def test_metric_crs_is_local_utm():
    assert METRIC_CRS == "EPSG:32649"


def test_stable_id_uses_natural_id():
    feature = GeoDataLoader().load_geojson("tree.json")["features"][0]
    assert generate_stable_id("tree", feature, 0) == "tree:1"


def test_stable_id_fallback_is_content_based_not_index_based():
    feature = {"geometry": {"type": "Point", "coordinates": [114.1, 22.5]},
               "properties": {"label": "no natural id"}}
    first = generate_stable_id("tree", feature, 0)
    second = generate_stable_id("tree", feature, 99)
    assert first == second
    assert first.startswith("tree:")


def test_dependencies_have_isolated_staging():
    a = GISDependencies(loader=GeoDataLoader())
    b = GISDependencies(loader=GeoDataLoader())
    a.visual_staging.append({"type": "Feature"})
    assert b.visual_staging == []


def test_chat_request_validation():
    with pytest.raises(ValidationError):
        ChatRequest(query="")
    with pytest.raises(ValidationError):
        ChatRequest(query="x", history=[{}] * 101)
    assert ChatRequest(query="ok").history == []
