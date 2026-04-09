# src\utils\geo_ops.py

import hashlib
import json
import re
from typing import Dict, Any, List

# --- Constants & Patterns ---
NOISE_KEYS = {'objectid', 'fid', 'pk', 'shape_area', 'shape_leng', 'layer'}
TITLE_PATTERNS = re.compile(r'(name|title|label|alias|caption|nme|名称|名字|标题)', re.IGNORECASE)
ID_PATTERNS = re.compile(r'(_?id|guid|uuid|key|uprn|code|ref)', re.IGNORECASE)

def get_property_schema(geojson: Dict[str, Any]) -> Dict[str, List[str]]:
    """提取图层的属性 Schema 和样例值，帮助 AI 决定过滤条件。"""
    features = geojson.get("features", [])
    if not features: return {}
    
    sample_props = features[0].get("properties", {})
    schema_info = {}
    for k in sample_props.keys():
        if k.lower() not in NOISE_KEYS:
            # 采集前 3 个非空值作为参考示例
            samples = list(set([
                str(f.get("properties", {}).get(k)) 
                for f in features[:50] if f.get("properties", {}).get(k)
            ]))[:3]
            schema_info[k] = samples
    return schema_info

def find_best_id(feature: Dict[str, Any], props: Dict[str, Any]) -> str:
    """Heuristically find the most suitable ID field."""
    # 1. Check GeoJSON standard level ID
    if feature.get("id") is not None:
        return str(feature["id"])

    # 2. Check properties for ID-like keys
    potential_keys = [k for k in props.keys() if ID_PATTERNS.search(k)]
    for k in potential_keys:
        val = str(props[k]).strip()
        if val and len(val) < 50:
            return val
    return ""

def find_best_name(props: Dict[str, Any]) -> str:
    """Heuristically find the most suitable display title."""
    if not props:
        return "Unnamed"

    keys = list(props.keys())
    
    # Strategy A: Semantic Match
    for k in keys:
        if TITLE_PATTERNS.search(k):
            val = str(props[k]).strip()
            if 0 < len(val) < 100:
                return val
    
    # Strategy B: First meaningful string
    for k in keys:
        if k.lower() not in NOISE_KEYS:
            val = str(props[k]).strip()
            if 2 < len(val) < 50:
                return val
                    
    return str(next(iter(props.values()))) if props else "Unnamed"

def generate_stable_id(layer_name: str, feature: Dict[str, Any], index: int) -> str:
    """Generates a consistent ID based on content if no natural ID is found."""
    props = feature.get("properties", {})
    found_id = find_best_id(feature, props)
    
    if found_id:
        return f"{layer_name}:{found_id}"
    
    # Hash-based fallback
    geom_str = json.dumps(feature.get("geometry"), sort_keys=True)
    prop_str = json.dumps(props, sort_keys=True)
    fingerprint = hashlib.md5((geom_str + prop_str).encode()).hexdigest()[:10]
    return f"{layer_name}:idx_{index}:{fingerprint}"

def dehydrate_geojson(geojson: Dict[str, Any], layer_name: str, limit: int = 50) -> Dict[str, Any]:
    """
    Refines GeoJSON into an AI-optimized Tabular JSON format (CSV-like).
    Returns a dict with 'cols' (headers) and 'rows' (data).
    """
    features = geojson.get("features", [])[:limit]
    if not features:
        return {"layer": layer_name, "cols": [], "rows": []}

    # Internal tracking for dynamic schema
    all_keys: List[str] = []
    key_map: Dict[str, int] = {}
    
    # Pre-define fixed columns for AI clarity
    fixed_cols = ["@id", "@title"]
    
    temp_rows = []
    for i, feature in enumerate(features):
        props = feature.get("properties", {})
        display_name = find_best_name(props)
        fid = generate_stable_id(layer_name, feature, i)
        
        row_props = {}
        for k, v in props.items():
            k_low = k.lower()
            v_str = str(v).strip() if v is not None else ""
            
            if (v_str and len(v_str) < 200 and 
                not k.startswith('_') and k_low not in NOISE_KEYS):
                if k not in key_map:
                    key_map[k] = len(all_keys)
                    all_keys.append(k)
                row_props[k] = v_str
        
        temp_rows.append({
            "@id": fid,
            "@title": display_name,
            **row_props
        })

    # Final conversion to "Compact Table" format (AI best practice)
    # This structure mimics a CSV but remains valid JSON
    headers = fixed_cols + all_keys
    final_rows = []
    for r in temp_rows:
        # Fill row in header order, use None/empty for missing to keep array alignment
        final_rows.append([r.get(h, "") for h in headers])

    return {
        "layer": layer_name,
        "schema": headers,
        "data": final_rows
    }

def estimate_compression(raw_data: Dict[str, Any], dehydrated_data: Dict[str, Any]):
    """Evaluates Token and Character compression ratios."""
    raw_str = json.dumps(raw_data, ensure_ascii=False, separators=(',', ':'))
    compact_str = json.dumps(dehydrated_data, ensure_ascii=False, separators=(',', ':'))
    
    raw_size = len(raw_str)
    compact_size = len(compact_str)
    ratio = (1 - compact_size / raw_size) * 100
    
    print("-" * 40)
    print(f"Compression Report:")
    print(f"Original: {raw_size} chars | Dehydrated: {compact_size} chars")
    print(f"Reduction: {ratio:.2f}%")
    print("-" * 40)

if __name__ == "__main__":
    import os
    # Assuming the structure provided in your environment
    file_path = os.path.join("data", "schools.json")
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
        
        # Testing with first 20 features
        sample_raw = {"features": raw_data.get("features", [])[:20]}
        compact_result = dehydrate_geojson(raw_data, "edu", limit=20)
        
        estimate_compression(sample_raw, compact_result)
        
        # Displaying result for inspection
        display_result = compact_result.copy()
        if len(display_result["data"]) > 1:
            # Show schema and only the first row for brevity
            display_result["data"] = [display_result["data"][0], "... (more rows)"]
            
        print(json.dumps(display_result, indent=2, ensure_ascii=False))