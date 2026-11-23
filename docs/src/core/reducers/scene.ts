/**
 * Pure scene reducer. Every command returns a new state (or the same reference
 * when nothing changed) and performs no I/O. This is the single source of
 * truth for scene transitions; adapters observe the result via `reconcile`.
 */

import type { BBox, GeoJsonFeature } from '../model/geo'
import {
  createEmptyScene,
  type LayerSpec,
  type SceneState,
  type ThemeId,
  type ViewportSnapshot,
} from '../model/scene'

export type SceneCommand =
  | { type: 'selectFeature'; feature: GeoJsonFeature | null }
  | { type: 'hoverFeature'; feature: GeoJsonFeature | null }
  | { type: 'setLayerVisibility'; id: string; visible: boolean }
  | { type: 'setLayerOpacity'; id: string; opacity: number }
  | { type: 'reorderLayers'; order: string[] }
  | { type: 'setViewport'; viewport: ViewportSnapshot }
  | { type: 'fitBounds'; bbox: BBox }
  | { type: 'clearFit' }
  | { type: 'setTheme'; theme: ThemeId }
  | { type: 'upsertLayer'; spec: LayerSpec }
  /** Mirror a whole ordered layer list (used by the Pinia mirror). */
  | { type: 'replaceLayers'; specs: LayerSpec[] }
  | { type: 'removeLayer'; id: string }
  | { type: 'removeLayersByRole'; role: LayerSpec['role'] }
  | { type: 'bumpRevision'; id: string }

function sameFeature(a: GeoJsonFeature | null, b: GeoJsonFeature | null): boolean {
  if (a === b) return true
  if (!a || !b) return false
  return a.id !== undefined && a.id === b.id
}

function updateLayer(
  state: SceneState,
  id: string,
  updater: (spec: LayerSpec) => LayerSpec,
): SceneState {
  const current = state.layers[id]
  if (!current) return state
  const nextLayer = updater(current)
  if (nextLayer === current) return state
  return { ...state, layers: { ...state.layers, [id]: nextLayer } }
}

function withSelectionSource(spec: LayerSpec, feature: GeoJsonFeature | null): LayerSpec {
  return {
    ...spec,
    source: { kind: 'geojson', features: feature ? [feature] : [] },
    revision: spec.revision + 1,
  }
}

export function sceneReducer(state: SceneState, cmd: SceneCommand): SceneState {
  switch (cmd.type) {
    case 'selectFeature': {
      if (sameFeature(state.selection, cmd.feature)) return state
      let next: SceneState = { ...state, selection: cmd.feature }
      // Singleton selection layers follow the selection automatically.
      for (const spec of Object.values(next.layers)) {
        if (spec.role === 'selection') next = updateLayer(next, spec.id, (s) => withSelectionSource(s, cmd.feature))
      }
      return next
    }

    case 'hoverFeature': {
      if (sameFeature(state.hover, cmd.feature)) return state
      return { ...state, hover: cmd.feature }
    }

    case 'setLayerVisibility': {
      return updateLayer(state, cmd.id, (spec) =>
        spec.visible === cmd.visible
          ? spec
          : { ...spec, visible: cmd.visible, revision: spec.revision + 1 },
      )
    }

    case 'setLayerOpacity': {
      return updateLayer(state, cmd.id, (spec) =>
        spec.opacity === cmd.opacity
          ? spec
          : { ...spec, opacity: cmd.opacity, revision: spec.revision + 1 },
      )
    }

    case 'reorderLayers': {
      const known = new Set(state.order)
      const requested = cmd.order.filter((id) => known.has(id))
      const remainder = state.order.filter((id) => !requested.includes(id))
      const nextOrder = [...requested, ...remainder]
      if (nextOrder.length === state.order.length && nextOrder.every((id, i) => id === state.order[i])) {
        return state
      }
      const layers = { ...state.layers }
      nextOrder.forEach((id, index) => {
        layers[id] = { ...layers[id], order: index }
      })
      return { ...state, order: nextOrder, layers }
    }

    case 'setViewport': {
      const v = cmd.viewport
      const p = state.viewport
      if (
        p.zoom === v.zoom &&
        p.bearing === v.bearing &&
        p.pitch === v.pitch &&
        p.center[0] === v.center[0] &&
        p.center[1] === v.center[1]
      ) {
        return state
      }
      return { ...state, viewport: { ...v, center: [...v.center] } }
    }

    case 'fitBounds':
      return { ...state, pendingFit: cmd.bbox }

    case 'clearFit':
      return state.pendingFit ? { ...state, pendingFit: null } : state

    case 'setTheme':
      return state.theme === cmd.theme ? state : { ...state, theme: cmd.theme }

    case 'upsertLayer': {
      const current = state.layers[cmd.spec.id]
      if (!current) {
        return {
          ...state,
          layers: { ...state.layers, [cmd.spec.id]: cmd.spec },
          order: [...state.order, cmd.spec.id],
        }
      }
      const spec: LayerSpec = {
        ...current,
        ...cmd.spec,
        // A merge always means "something changed": advance past both the
        // stored and the incoming counter so adapters rebuild the layer.
        revision: Math.max(current.revision, cmd.spec.revision) + 1,
      }
      return { ...state, layers: { ...state.layers, [spec.id]: spec } }
    }

    case 'replaceLayers': {
      const layers: Record<string, LayerSpec> = {}
      const order: string[] = []
      cmd.specs.forEach((spec, index) => {
        layers[spec.id] = { ...spec, order: spec.order ?? index }
        order.push(spec.id)
      })
      return { ...state, layers, order }
    }

    case 'removeLayer': {
      if (!state.layers[cmd.id]) return state
      const layers = { ...state.layers }
      delete layers[cmd.id]
      return { ...state, layers, order: state.order.filter((id) => id !== cmd.id) }
    }

    case 'removeLayersByRole': {
      const doomed = Object.values(state.layers)
        .filter((spec) => spec.role === cmd.role)
        .map((spec) => spec.id)
      if (!doomed.length) return state
      return doomed.reduce((acc, id) => sceneReducer(acc, { type: 'removeLayer', id }), state)
    }

    case 'bumpRevision':
      return updateLayer(state, cmd.id, (spec) => ({ ...spec, revision: spec.revision + 1 }))

    default:
      return state
  }
}

export { createEmptyScene }
