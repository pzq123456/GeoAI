import pyproj
import asyncio
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

class GeoDataLoader:
    def __init__(self, base_dir: Path = DATA_DIR):
        self.base_path = base_dir

    def load_geojson(self, filename: str) -> Dict[str, Any]:
        file_path = self.base_path / filename
        if not file_path.exists():
            raise FileNotFoundError(f"Missing data file: {file_path}")
        import json
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def get_transformer(from_crs="EPSG:4326", to_crs="EPSG:3857"):
        return pyproj.Transformer.from_crs(from_crs, to_crs, always_xy=True).transform

@dataclass
class GISDependencies:
    loader: GeoDataLoader
    # 异步队列：用于 Agent 运行期间实时推送工具执行状态
    status_queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    # 中间空间：存储巨大的 GeoJSON，防止其进入 LLM 上下文（Token 隔离）
    visual_buffer: Optional[Dict[str, Any]] = None

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
    query: str
    history: List[Dict[str, Any]] = []