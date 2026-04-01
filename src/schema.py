import json
import pyproj
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel

# 路径配置
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

class GeoDataLoader:
    """负责从磁盘加载静态地理数据"""
    def __init__(self, base_dir: Path = DATA_DIR):
        self.base_path = base_dir

    def load_geojson(self, filename: str) -> Dict[str, Any]:
        file_path = self.base_path / filename
        if not file_path.exists():
            raise FileNotFoundError(f"Missing data file: {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def get_transformer(from_crs="EPSG:4326", to_crs="EPSG:3857"):
        return pyproj.Transformer.from_crs(from_crs, to_crs, always_xy=True).transform

@dataclass
class GISDependencies:
    """AI 运行时的依赖项"""
    loader: GeoDataLoader
    visual_buffer: Optional[Dict[str, Any]] = None
    status_updates: Optional[List[str]] = None 

    def add_status(self, msg: str):
        if self.status_updates is not None:
            self.status_updates.append(msg)

# AI 输出结构
class ClarificationResponse(BaseModel):
    guidance: str
    suggestions: List[str]

class GISAnalysisOutput(BaseModel):
    analysis_steps: List[str]
    final_report: str
    visualization_status: str

# API 请求结构
class ChatRequest(BaseModel):
    query: str
    history: List[Dict[str, Any]] = []