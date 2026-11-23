import json
import os
from typing import Callable, Any
import httpx
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.deepseek import DeepSeekProvider

from .schema import GISDependencies, GISAnalysisOutput, ClarificationResponse
from .prompts import get_system_instructions
from .tools import discovery, analysis, visualization


def _build_provider() -> DeepSeekProvider:
    """Build the DeepSeek provider with an explicit HTTP client.

    On this machine httpx's default ``trust_env=True`` picks up a stale Windows
    system proxy (127.0.0.1:7890) whose TLS handshake fails, producing
    ``ModelAPIError: Connection error``. ``trust_env=False`` talks directly to
    the API. Override with GEOAI_HTTP_TRUST_ENV=1 if a working proxy is needed.
    """
    trust_env = os.getenv('GEOAI_HTTP_TRUST_ENV', '').strip().lower() in {'1', 'true', 'yes'}
    http_client = httpx.AsyncClient(trust_env=trust_env, timeout=90.0)
    return DeepSeekProvider(
        api_key=os.getenv('DEEPSEEK_API_KEY') or '',
        http_client=http_client,
    )


# 1. 模型配置 (推荐使用 DeepSeek 官方 Provider)
model = OpenAIChatModel(
    model_name='deepseek-chat',
    provider=_build_provider(),
)

# 2. 工具集聚合 (显式类型标注有助于 IDE 检查)
GIS_TOOLS: list[Callable[..., Any]] = [
    discovery.list_layers,
    discovery.query_layer_features,

    analysis.spatial_query_nearby,
    analysis.measure_tree_feature,
    analysis.calculate_group_convex_hull,
    analysis.analyze_tree_distribution_balance,

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
    retries=2,
)


@gis_expert.instructions
def inject_map_context(ctx: RunContext[GISDependencies]) -> str | None:
    """Turn the frontend's map snapshot into per-run instructions.

    The snapshot is scoped to one request: no cross-run memory, no global
    mutable state. Keeping it in the context (rather than the query string)
    means the displayed user message stays clean.
    """
    context = ctx.deps.context
    if not context:
        return None

    feature = context.get("selectedFeature")
    viewport = context.get("viewport") or {}
    layers = context.get("layers") or []

    lines = [
        "# 当前地图上下文（前端注入，仅本次运行有效）",
        f"- 可见图层: {', '.join(layers) if layers else '无'}",
        f"- 视口中心: {viewport.get('center')}, zoom: {viewport.get('zoom')}",
    ]
    if feature:
        props = feature.get("properties") or {}
        preview = dict(list(props.items())[:20])
        lines.append(
            f"- 选中要素: id={feature.get('id')}, geometry={feature.get('geometryType')}"
        )
        lines.append(
            "- 选中要素属性(JSON): "
            + json.dumps(preview, ensure_ascii=False, default=str)[:2000]
        )
    else:
        lines.append("- 选中要素: 无（用户未点选地图要素）")

    return "\n".join(lines)