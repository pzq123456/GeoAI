/**
 * Agent → Map bridge. Turns a final agent result into a declarative layer
 * spec; the adapter is responsible for materialising a deck.gl layer.
 */

import type { FeatureCollection, RGBAColor } from '../model/geo'
import type { LayerSpec } from '../model/scene'

export interface AgentResult {
  geojson?: FeatureCollection | null
  report?: unknown
  history?: unknown[]
  run_id?: string
}

export const RESULT_LAYER_ID = 'AI-Result'
export const RESULT_LAYER_COLOR: RGBAColor = [255, 140, 66, 180]

/** Distinguishing colours for successive result layers. */
const RESULT_PALETTE: RGBAColor[] = [
  [255, 140, 66, 200],
  [168, 85, 247, 200],
  [34, 197, 94, 200],
  [56, 189, 248, 200],
  [244, 63, 94, 200],
]

export function resultColor(index: number): RGBAColor {
  return RESULT_PALETTE[Math.max(0, index - 1) % RESULT_PALETTE.length]
}

/** Convert an agent result to a result-role layer, or `null` if it has no features. */
export function resultToLayer(
  result: AgentResult,
  revision = 1,
  options: { layerId?: string; turnIndex?: number; visible?: boolean } = {},
): LayerSpec | null {
  const collection = result.geojson
  if (!collection || !Array.isArray(collection.features) || collection.features.length === 0) {
    return null
  }
  const turnIndex = options.turnIndex ?? 1
  return {
    id: options.layerId ?? RESULT_LAYER_ID,
    role: 'result',
    source: { kind: 'geojson-collection', collection },
    style: {
      color: options.turnIndex ? resultColor(options.turnIndex) : RESULT_LAYER_COLOR,
      lineWidth: 2,
      filled: true,
      stroked: true,
    },
    visible: options.visible ?? true,
    opacity: 0.8,
    order: Number.MAX_SAFE_INTEGER - turnIndex,
    revision,
  }
}
