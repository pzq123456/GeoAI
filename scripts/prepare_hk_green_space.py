"""Build a compact HK green-space dataset for the GeoAI demo map.

Downloads three Hong Kong government open-data GeoJSON files from the
``funglkf/hk-geodata`` GitHub mirror, normalises them into one FeatureCollection
and writes a small metadata sidecar (bbox + counts) for the frontend.

Output:
    data/demo/hk-green-space.json
    data/demo/hk-green-space.meta.json

Stdlib only, deterministic — safe to re-run.
"""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "demo"
OUT = OUT_DIR / "hk-green-space.json"
META = OUT_DIR / "hk-green-space.meta.json"

BASE_URL = "https://raw.githubusercontent.com/funglkf/hk-geodata/main/static/json/"
SOURCES = {
    "park": "Parks_Zoos_and_Gardens.geojson",
    "open_space": "Public_Open_Space.geojson",
    "country_park": "Country_Parks.geojson",
}

# Rough Hong Kong bounds; rejects stray/invalid coordinates.
LON_RANGE = (113.0, 115.0)
LAT_RANGE = (21.0, 23.0)


def download(filename: str) -> dict[str, Any]:
    request = urllib.request.Request(
        BASE_URL + filename,
        headers={"User-Agent": "GeoAI-demo/0.1 (Hong Kong green-space demo)"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def valid_lonlat(value: Any) -> list[float] | None:
    if not isinstance(value, (list, tuple)) or len(value) < 2:
        return None
    try:
        lon, lat = float(value[0]), float(value[1])
    except (TypeError, ValueError):
        return None
    if not (LON_RANGE[0] <= lon <= LON_RANGE[1] and LAT_RANGE[0] <= lat <= LAT_RANGE[1]):
        return None
    return [lon, lat]


def main() -> int:
    features: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    bounds = [180.0, 90.0, -180.0, -90.0]

    for category, filename in SOURCES.items():
        raw = download(filename)
        kept = 0
        for index, feature in enumerate(raw.get("features", [])):
            geometry = feature.get("geometry") or {}
            props = feature.get("properties") or {}
            if geometry.get("type") == "Point":
                point = valid_lonlat(geometry.get("coordinates"))
                geometry_out = {"type": "Point", "coordinates": point} if point else None
            elif geometry.get("type") == "MultiPoint":
                points = [valid_lonlat(c) for c in geometry.get("coordinates", [])]
                points = [p for p in points if p is not None]
                geometry_out = {"type": "MultiPoint", "coordinates": points} if points else None
            else:
                continue
            if geometry_out is None:
                continue

            for point in (
                geometry_out["coordinates"]
                if geometry_out["type"] == "MultiPoint"
                else [geometry_out["coordinates"]]
            ):
                bounds[0] = min(bounds[0], point[0])
                bounds[1] = min(bounds[1], point[1])
                bounds[2] = max(bounds[2], point[0])
                bounds[3] = max(bounds[3], point[1])

            features.append(
                {
                    "type": "Feature",
                    "id": f"{category}-{props.get('GMID') or index + 1}",
                    "geometry": geometry_out,
                    "properties": {
                        "category": category,
                        "name": props.get("Facility Name") or props.get("Name") or "N.A.",
                        "name_zh": props.get("設施名稱") or props.get("名稱") or "",
                        "district": props.get("District") or props.get("Relevant District Council") or "",
                        "address": props.get("Address") or "",
                        "area_m2": props.get("Area (about) (m²)") or "",
                        "source": filename,
                    },
                }
            )
            kept += 1
        counts[category] = kept

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    META.write_text(
        json.dumps(
            {
                "bbox": bounds,
                "counts": counts,
                "total": len(features),
                "source_repo": "funglkf/hk-geodata",
                "source_base_url": BASE_URL,
                "attribution": "Hong Kong Government open data (ODbL / open data licence)",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"wrote {len(features)} features to {OUT}")
    print(f"counts={counts} bbox={bounds}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
