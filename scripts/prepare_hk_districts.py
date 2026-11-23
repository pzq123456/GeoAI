"""Build a compact Hong Kong 18-district boundary layer for the demo map.

Each district comes from the ``Paulkit/HKMap`` GitHub repo (one GeoJSON per
district). The script normalises Polygon / MultiPolygon / GeometryCollection
geometries, simplifies them slightly, merges everything into one
FeatureCollection and writes a bbox sidecar.

    python scripts/prepare_hk_districts.py
    python scripts/prepare_hk_districts.py --local-dir tmp/hk-district-raw
"""

from __future__ import annotations

import argparse
import json
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from shapely.geometry import GeometryCollection, MultiPolygon, Polygon, mapping, shape

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "demo"
OUT = OUT_DIR / "hk-districts.json"
META = OUT_DIR / "hk-districts.meta.json"

BASE_URL = "https://raw.githubusercontent.com/Paulkit/HKMap/master/json/"
DISTRICTS = [
    "Central and Western", "Eastern", "Islands", "Kowloon City", "Kwai Tsing",
    "Kwun Tong", "North", "Sai Kung", "Sha Tin", "Sham Shui Po", "Southern",
    "Tai Po", "Tsuen Wan", "Tuen Mun", "Wan Chai", "Wong Tai Sin",
    "Yau Tsim Mong", "Yuen Long",
]
# ~15 m at HK latitude — enough to keep shapes recognisable while shrinking files.
SIMPLIFY_DEG = 0.00015


def fetch(name: str, local_dir: Path | None) -> dict[str, Any]:
    if local_dir is not None:
        path = local_dir / f"{name}.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    url = BASE_URL + urllib.parse.quote(name) + ".json"
    request = urllib.request.Request(url, headers={"User-Agent": "GeoAI-demo/0.1 (HK demo)"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)


def to_polygons(geometry: Any) -> MultiPolygon | None:
    geom = shape(geometry)
    polygons: list[Polygon] = []
    if isinstance(geom, Polygon):
        polygons = [geom]
    elif isinstance(geom, MultiPolygon):
        polygons = list(geom.geoms)
    elif isinstance(geom, GeometryCollection):
        polygons = [g for g in geom.geoms if isinstance(g, Polygon)]
        polygons += [p for g in geom.geoms if isinstance(g, MultiPolygon) for p in g.geoms]
    if not polygons:
        return None
    merged = MultiPolygon(polygons).simplify(SIMPLIFY_DEG, preserve_topology=True)
    return merged if not merged.is_empty else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--local-dir", type=Path, default=None)
    args = parser.parse_args()

    features: list[dict[str, Any]] = []
    for index, name in enumerate(DISTRICTS):
        raw = fetch(name, args.local_dir)
        feature = (raw.get("features") or [None])[0]
        if not feature:
            print(f"skip {name}: no feature")
            continue
        geometry = to_polygons(feature.get("geometry"))
        if geometry is None:
            print(f"skip {name}: no polygon geometry")
            continue
        props = feature.get("properties") or {}
        features.append(
            {
                "type": "Feature",
                "id": f"district-{index + 1}",
                "geometry": mapping(geometry),
                "properties": {
                    "name": props.get("name") or name,
                    "name_en": name,
                    "kind": "district",
                },
            }
        )

    bounds = [180.0, 90.0, -180.0, -90.0]
    for feature in features:
        minx, miny, maxx, maxy = shape(feature["geometry"]).bounds
        bounds[0] = min(bounds[0], minx)
        bounds[1] = min(bounds[1], miny)
        bounds[2] = max(bounds[2], maxx)
        bounds[3] = max(bounds[3], maxy)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    META.write_text(
        json.dumps(
            {
                "bbox": bounds,
                "count": len(features),
                "source_repo": "Paulkit/HKMap",
                "source_base_url": BASE_URL,
                "attribution": "Hong Kong district boundaries (HKMap / OpenStreetMap-derived)",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"wrote {len(features)} districts to {OUT} (bbox={bounds})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
