/** Mirror the legacy LayerGroup into core `LayerSpec`s for the renderer/selectors. */

import type { LayerItem } from '@/composables/useLayerGroup'
import {
  createEmptyScene,
  sceneReducer,
  type GeoJsonFeature,
  type LayerRole,
  type LayerSpec,
  type RGBAColor,
  type SceneState,
  type ThemeId,
  type ViewportSnapshot,
} from '@/core'
import { ROLE_COLOR } from './deckStyle'

const DEFAULT_COLOR: RGBAColor = [140, 150, 165, 210]

export function inferRole(id: string): LayerRole {
  if (id === 'Highlight-Layer') return 'selection'
  if (id.startsWith('AI-Result')) return 'result'
  if (id.startsWith('osm-') || id === 'tree-Layer') return 'analysis'
  if (id.startsWith('hk-')) return 'theme'
  return 'base'
}

function dataFeatures(data: unknown): GeoJsonFeature[] {
  if (Array.isArray(data)) return data as GeoJsonFeature[]
  if (typeof data === 'object' && data !== null && Array.isArray((data as { features?: unknown }).features)) {
    return (data as { features: GeoJsonFeature[] }).features
  }
  return []
}

function specColor(item: LayerItem, role: LayerRole): RGBAColor {
  if (ROLE_COLOR[role]) return ROLE_COLOR[role]!
  const fromProps = item.state?.getFillColor
  return Array.isArray(fromProps) && fromProps.length >= 4
    ? (fromProps.slice(0, 4) as RGBAColor)
    : DEFAULT_COLOR
}

export function layerToSpec(item: LayerItem, index = 0): LayerSpec {
  const role = item.role ?? inferRole(item.id)
  return {
    id: item.id,
    role,
    source: { kind: 'geojson', features: dataFeatures(item.data) },
    style: {
      color: specColor(item, role),
      filled: true,
      stroked: true,
    },
    visible: item.visible,
    opacity: item.opacity,
    order: index,
    revision: item.revision ?? 0,
  }
}

export interface SceneMirrorInput {
  layers: LayerItem[]
  selection: GeoJsonFeature | null
  hover: GeoJsonFeature | null
  viewport: ViewportSnapshot
  theme: ThemeId
}

/** Pure projection: legacy UI registry → canonical core scene state. */
export function buildScene(input: SceneMirrorInput): SceneState {
  let scene = createEmptyScene(input.theme)
  scene = sceneReducer(scene, {
    type: 'replaceLayers',
    specs: input.layers.map((layer, index) => layerToSpec(layer, index)),
  })
  scene = sceneReducer(scene, { type: 'setViewport', viewport: input.viewport })
  scene = sceneReducer(scene, { type: 'selectFeature', feature: input.selection })
  scene = sceneReducer(scene, { type: 'hoverFeature', feature: input.hover })
  return scene
}
