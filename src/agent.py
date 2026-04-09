import os
from typing import Callable, Any
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.deepseek import DeepSeekProvider

from .schema import GISDependencies, GISAnalysisOutput, ClarificationResponse
from .prompts import get_system_instructions
from .tools import discovery, analysis, visualization

# 1. 模型配置 (推荐使用 DeepSeek 官方 Provider)
model = OpenAIChatModel(
    model_name='deepseek-chat',
    provider=DeepSeekProvider(api_key=os.getenv('DEEPSEEK_API_KEY') or ""),
)

# 2. 工具集聚合 (显式类型标注有助于 IDE 检查)
GIS_TOOLS: list[Callable[..., Any]] = [
    discovery.list_layers,
    discovery.query_layer_features,
    
    # discovery.search_features_fuzzy,
    # discovery.filter_features_by_property,
    # discovery.inspect_layer_metadata,
    
    analysis.spatial_query_nearby,
    analysis.universal_measure_by_ref,
    analysis.calculate_group_convex_hull,
    analysis.analyze_service_coverage,
    
    visualization.add_to_map,
    visualization.get_map_inventory,
    visualization.clear_visual_staging,
]

# 3. Agent 实例化 (核心优化：显式指定泛型参数)
# Agent[DepsType, ResultType]
gis_expert: Agent[GISDependencies, GISAnalysisOutput | ClarificationResponse] = Agent(
    model=model,
    deps_type=GISDependencies,
    output_type=GISAnalysisOutput | ClarificationResponse,
    instructions=get_system_instructions(),
    tools=GIS_TOOLS,
)