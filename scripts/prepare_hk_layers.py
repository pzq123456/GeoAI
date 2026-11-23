"""Build compact, themed Hong Kong point layers for the GeoAI demo.

Downloads curated datasets from the ``funglkf/hk-geodata`` GitHub mirror (a
mirror of Hong Kong government open data), normalises them into one
FeatureCollection per theme, and writes a metadata sidecar for each layer.

Outputs (per theme ``t``):
    data/hk-<t>.json
    data/meta/hk-<t>.meta.json

The JSON files live at the top level of ``data/`` so the backend's
``list_layers`` can discover them as real GIS layers. Metadata goes in a
subdirectory so it is not mistaken for a layer by ``GeoDataLoader``.

Stdlib only, deterministic — safe to re-run.

Usage:
    python scripts/prepare_hk_layers.py                 # all themes
    python scripts/prepare_hk_layers.py health sports   # selected themes
    python scripts/prepare_hk_layers.py --list
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
META_DIR = DATA_DIR / "meta"

BASE_URL = "https://raw.githubusercontent.com/funglkf/hk-geodata/main/static/json/"
SOURCE_REPO = "funglkf/hk-geodata"
ATTRIBUTION = "Hong Kong Government open data (ODbL / open data licence)"

# Rough Hong Kong bounds; rejects stray/invalid coordinates.
LON_RANGE = (113.0, 115.0)
LAT_RANGE = (21.0, 23.0)

# 5 decimals ≈ 1 m at Hong Kong's latitude. The source files carry 8 decimals
# (millimetre precision), which is pure noise for a city-scale map.
COORD_DECIMALS = 5

# theme -> {category slug: source filename}
THEMES: dict[str, dict[str, str]] = {
    "environment": {
        "air_quality": "Air_Quality_Monitoring_Network_of_Hong_Kong.geojson",
        "weather_station": "Network_of_Weather_Stations_in_Hong_Kong.geojson",
        "waste_facility": "Waste_Management_Facilities.geojson",
        "recycling_point": "Recycling_Organisations_and_Collection_Points.geojson",
        "marine_park": "Marine_Parks.geojson",
        "marine_reserve": "Marine_Reserve.geojson",
        "red_tide": "Red_Tide_Incident.geojson",
    },
    "health": {
        "hospital": "Hospitals_under_the_Hospital_Authority.geojson",
        "clinic": "Clinics_Health_Centres_under_the_Department_of_Health.geojson",
        "general_outpatient": "General_Outpatient_Clinics_under_the_Hospital_Authority.geojson",
        "specialist_outpatient": "Specialist_Outpatient_Clinics_under_the_Hospital_Authority.geojson",
        "district_health_centre": "District_Health_Centres.geojson",
        "district_health_express": "District_Health_Centre_Expresses.geojson",
    },
    "education": {
        "kindergarten": "Kindergartens.geojson",
        "primary_aided": "Aided_Primary_Schools.geojson",
        "primary_government": "Government_Primary_Schools.geojson",
        "secondary_aided": "Aided_Secondary_Schools.geojson",
        "secondary_government": "Government_Secondary_Schools.geojson",
        "primary_international": "International_Schools_Primary_.geojson",
        "secondary_international": "International_Schools_Secondary_.geojson",
        "higher_education": "Higher_Education_Institutions.geojson",
        "ugc_funded": "UGC-Funded_Institutions.geojson",
    },
    "sports": {
        "swimming_pool": "Swimming_Pools.geojson",
        "sports_centre": "Sports_Centres.geojson",
        "sports_ground": "Sports_Grounds.geojson",
        "tennis_court": "Tennis_Courts.geojson",
        "badminton_court": "Badminton_Courts.geojson",
        "basketball_court": "Basketball_Courts.geojson",
        "beach": "Beaches.geojson",
        "cycling_site": "Cycling_Sites.geojson",
        "stadium": "Stadia.geojson",
        "museum": "Museums.geojson",
        "performance_venue": "Performance_Venues.geojson",
    },
    "services": {
        "library": "Libraries.geojson",
        "post_office": "Post_Offices.geojson",
        "public_market": "Public_Market_Information.geojson",
        "police_station": "Police_Stations_Districts_Divisons_.geojson",
        "fehd_facility": "FEHD_facility_and_service_locations.geojson",
        "street_posting_box": "Street_Posting_Boxes.geojson",
        "smart_lamppost": "Summary_of_Functions_on_Smart_Lampposts.geojson",
        "country_park_visitor_centre": "Visitor_Centres_of_Country_Parks.geojson",
        "country_park_water": "Country_Park_Water_Filling_Station.geojson",
    },
    "wifi": {
        "wifi_hotspot": "Wi-Fi_HK_Locations.geojson",
    },
}

# Common property keys across the mirror's facility datasets.
NAME_KEYS = ("Facility Name", "Name", "設施名稱", "名稱")
NAME_ZH_KEYS = ("設施名稱", "名稱", "设施名称")
DISTRICT_KEYS = ("District", "Relevant District Council", "的地區", "地區")
ADDRESS_KEYS = ("Address", "地址")
TYPE_KEYS = (
    "Facility Type",
    "Library Type",
    "Types of Weather Station",
    "Types of Air Quality Monitoring Station",
    "Venue Type",
    "Organisation",
)
PHONE_KEYS = ("Telephone", "電話")
WEB_KEYS = ("Website", "網址")
HOURS_KEYS = ("Opening Hours", "開放時間")
UPDATE_KEYS = ("Last Update",)


def _first(props: dict[str, Any], keys: tuple[str, ...]) -> str:
    """Return the first non-empty string value for ``keys``."""
    for key in keys:
        value = props.get(key)
        if isinstance(value, str) and value.strip() and value.strip().upper() != "N.A.":
            return value.strip()
    return ""


def download(filename: str, retries: int = 3) -> dict[str, Any]:
    url = BASE_URL + filename
    request = urllib.request.Request(
        url, headers={"User-Agent": "GeoAI-demo/0.2 (Hong Kong open-data layers)"}
    )
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001 - network errors vary by platform
            last_error = exc
            if attempt + 1 < retries:
                time.sleep(1 + attempt)

    # Some Windows networks drop Python's TLS handshake while curl succeeds.
    if shutil.which("curl.exe"):
        try:
            result = subprocess.run(
                [
                    "curl.exe",
                    "--ssl-no-revoke",
                    "--silent",
                    "--show-error",
                    "--fail",
                    "--max-time",
                    "120",
                    "-A",
                    "GeoAI-demo/0.2 (Hong Kong open-data layers)",
                    url,
                ],
                capture_output=True,
                check=True,
            )
            return json.loads(result.stdout.decode("utf-8"))
        except (subprocess.CalledProcessError, UnicodeDecodeError, ValueError) as exc:
            last_error = exc

    raise RuntimeError(f"failed to download {filename}: {last_error}")


def valid_lonlat(value: Any) -> list[float] | None:
    if not isinstance(value, (list, tuple)) or len(value) < 2:
        return None
    try:
        lon, lat = float(value[0]), float(value[1])
    except (TypeError, ValueError):
        return None
    if not (LON_RANGE[0] <= lon <= LON_RANGE[1] and LAT_RANGE[0] <= lat <= LAT_RANGE[1]):
        return None
    return [round(lon, COORD_DECIMALS), round(lat, COORD_DECIMALS)]


def normalise(
    feature: dict[str, Any], category: str, filename: str, index: int
) -> dict[str, Any] | None:
    geometry = feature.get("geometry") or {}
    if geometry.get("type") == "Point":
        point = valid_lonlat(geometry.get("coordinates"))
        geometry_out = {"type": "Point", "coordinates": point} if point else None
    elif geometry.get("type") == "MultiPoint":
        points = [valid_lonlat(c) for c in geometry.get("coordinates", [])]
        points = [p for p in points if p is not None]
        geometry_out = {"type": "MultiPoint", "coordinates": points} if points else None
    else:
        return None
    if geometry_out is None:
        return None

    props = feature.get("properties") or {}
    gmid = props.get("GMID")
    properties: dict[str, Any] = {
        "category": category,
        "name": _first(props, NAME_KEYS) or "N.A.",
    }
    # Only emit optional fields that actually carry data. Many source columns
    # are empty for every row (e.g. facility_type in education/health), and
    # storing thousands of empty strings was a large share of the file size.
    for key, keys in (
        ("name_zh", NAME_ZH_KEYS),
        ("district", DISTRICT_KEYS),
        ("address", ADDRESS_KEYS),
        ("facility_type", TYPE_KEYS),
        ("telephone", PHONE_KEYS),
        ("website", WEB_KEYS),
        ("opening_hours", HOURS_KEYS),
        ("last_update", UPDATE_KEYS),
    ):
        value = _first(props, keys)
        if value:
            properties[key] = value
    properties["source"] = filename

    return {
        "type": "Feature",
        "id": f"{category}-{gmid or index + 1}",
        "geometry": geometry_out,
        "properties": properties,
    }


def dedup_key(feature: dict[str, Any]) -> tuple[Any, ...]:
    """Identity for a point: category + name + rounded coordinate.

    The upstream mirror contains duplicate rows (same facility repeated), and
    the Wi-Fi dataset lists several rooms of one venue at the same building
    coordinate. For a map those copies are indistinguishable, so keep one.
    """
    props = feature["properties"]
    geometry = feature["geometry"]
    if geometry["type"] == "Point":
        coord = tuple(geometry["coordinates"][:2])
    else:
        first = geometry["coordinates"][0] if geometry["coordinates"] else [0, 0]
        coord = tuple(first[:2])
    return (props.get("category", ""), props.get("name", "").strip().lower(), coord)


def build_theme(sources: dict[str, str]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    features: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    skipped: dict[str, int] = {}
    duplicates: dict[str, int] = {}
    seen: set[tuple[Any, ...]] = set()
    bounds = [180.0, 90.0, -180.0, -90.0]

    for category, filename in sources.items():
        raw = download(filename)
        kept = 0
        dropped = 0
        merged = 0
        for index, feature in enumerate(raw.get("features", [])):
            normalised = normalise(feature, category, filename, index)
            if normalised is None:
                dropped += 1
                continue
            key = dedup_key(normalised)
            if key in seen:
                merged += 1
                continue
            seen.add(key)
            geometry = normalised["geometry"]
            points = (
                geometry["coordinates"]
                if geometry["type"] == "MultiPoint"
                else [geometry["coordinates"]]
            )
            for point in points:
                bounds[0] = min(bounds[0], point[0])
                bounds[1] = min(bounds[1], point[1])
                bounds[2] = max(bounds[2], point[0])
                bounds[3] = max(bounds[3], point[1])
            features.append(normalised)
            kept += 1
        counts[category] = kept
        if dropped:
            skipped[filename] = dropped
        if merged:
            duplicates[category] = merged
        print(f"  {category:28s} {kept:5d} points ({dropped} skipped, {merged} merged)")

    meta = {
        "bbox": bounds if features else [],
        "counts": counts,
        "total": len(features),
        "skipped": skipped,
        "duplicates_removed": duplicates,
        "coord_decimals": COORD_DECIMALS,
        "sources": dict(sources),
        "source_repo": SOURCE_REPO,
        "source_base_url": BASE_URL,
        "attribution": ATTRIBUTION,
    }
    return features, meta


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("themes", nargs="*", help="themes to build (default: all)")
    parser.add_argument("--list", action="store_true", help="list available themes and exit")
    args = parser.parse_args()

    if args.list:
        for theme, sources in THEMES.items():
            print(f"{theme}: {len(sources)} datasets")
        return 0

    selected = args.themes or list(THEMES)
    unknown = [theme for theme in selected if theme not in THEMES]
    if unknown:
        parser.error(f"unknown theme(s): {', '.join(unknown)}")

    META_DIR.mkdir(parents=True, exist_ok=True)
    for theme in selected:
        print(f"[{theme}] downloading {len(THEMES[theme])} datasets from {SOURCE_REPO} ...")
        features, meta = build_theme(THEMES[theme])
        out = DATA_DIR / f"hk-{theme}.json"
        meta_out = META_DIR / f"hk-{theme}.meta.json"
        out.write_text(
            json.dumps(
                {"type": "FeatureCollection", "features": features},
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            encoding="utf-8",
        )
        meta_out.write_text(
            json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"  -> {out.name}: {meta['total']} features; bbox={meta['bbox']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
