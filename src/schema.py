import pyproj
import asyncio
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

# Hong Kong falls in UTM zone 49N. Web Mercator overstates area by ~17% at
# this latitude, so metric computations use a local projections instead.
METRIC_CRS = "EPSG:32649"

def _trim_coordinates(value: Any) -> Any:
    """Shapely only accepts 2D/3D coordinates; GIS exports often carry a 4th
    measure column (and sentinel values such as -1.8e308). Drop anything beyond
    x/y so every analysis tool can consume the data safely."""
    if isinstance(value, (list, tuple)):
        if value and all(isinstance(v, (int, float)) for v in value):
            return list(value[:2])
        return [_trim_coordinates(v) for v in value]
    return value


class GeoDataLoader:
    def __init__(self, base_dir: Path = DATA_DIR):
        self.base_path = base_dir

    def load_geojson(self, filename: str) -> Dict[str, Any]:
        """Load a dataset from the data directory.

        Only dataset stems discovered in ``base_path`` are accepted. This keeps
        the loader simple for the single-dataset project and prevents an LLM
        supplied layer name from escaping the data directory.
        """
        stem = Path(filename).stem
        available = {p.stem for p in self.base_path.glob("*.json")}
        if stem not in available:
            raise ValueError(f"Unknown layer: {stem!r}. Available: {sorted(available)}")

        file_path = (self.base_path / f"{stem}.json").resolve()
        if not file_path.is_relative_to(self.base_path.resolve()):
            raise ValueError("Path escapes the data directory")

        import json
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for feature in data.get("features", []):
            geometry = feature.get("geometry")
            if geometry and "coordinates" in geometry:
                geometry["coordinates"] = _trim_coordinates(geometry["coordinates"])
        return data

    @staticmethod
    def get_transformer(from_crs="EPSG:4326", to_crs="EPSG:3857"):
        return pyproj.Transformer.from_crs(from_crs, to_crs, always_xy=True).transform

@dataclass
class GISDependencies:
    loader: GeoDataLoader
    # 异步队列：用于 Agent 运行期间实时推送工具执行状态
    status_queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    
    # 【新增/修改】可视化抽屉：用于存储 AI 链式调用过程中产生的所有要素
    # 使用 field 确保每个实例都有独立的列表
    visual_staging: List[Dict[str, Any]] = field(default_factory=list)
    # Serialisable snapshot of map state supplied by the frontend (selection,
    # viewport, visible layers). Injected as dynamic instructions on each run.
    context: Dict[str, Any] = field(default_factory=dict)

    def add_status(self, msg: str):
        self.status_queue.put_nowait(msg)

# 定义结构化输出模型
class ClarificationResponse(BaseModel):
    guidance: str
    suggestions: List[str]

class GISAnalysisOutput(BaseModel):
    analysis_steps: List[str]
    final_report: str
    visualization_status: str

class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    history: List[Dict[str, Any]] = Field(default_factory=list, max_length=100)
    context: Dict[str, Any] = Field(default_factory=dict)