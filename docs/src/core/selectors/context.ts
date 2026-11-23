/**
 * Map → Agent bridge. Produces the same serialisable context shape the
 * historical `useChatLogic` built, but as a pure selector over `SceneState`.
 */

import type { GeoJsonFeature } from '../model/geo'
import type { SceneState } from '../model/scene'

export interface AgentContext {
  selectedFeature: {
    id: string | number | undefined
    properties: Record<string, unknown>
    geometryType: string | null
  } | null
  viewport: { center: [number, number]; zoom: number }
  layers: string[]
}

function selectionSnapshot(feature: GeoJsonFeature | null): AgentContext['selectedFeature'] {
  if (!feature) return null
  return {
    id: feature.id,
    properties: feature.properties,
    geometryType: feature.geometry?.type ?? null,
  }
}

export function buildContext(scene: SceneState): AgentContext {
  const layers = scene.order
    .map((id) => scene.layers[id])
    .filter((spec) => spec && spec.visible)
    .map((spec) => spec.id)

  return {
    selectedFeature: selectionSnapshot(scene.selection),
    viewport: {
      center: [...scene.viewport.center] as [number, number],
      zoom: scene.viewport.zoom,
    },
    layers,
  }
}
