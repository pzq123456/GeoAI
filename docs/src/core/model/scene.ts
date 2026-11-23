/** Framework-free scene model. No Vue / Pinia / deck.gl / MapLibre imports. */

import type { BBox, FeatureCollection, GeoJsonFeature, RGBAColor } from './geo'

/** Singleton roles replace magic ids such as `'Highlight-Layer'` / `'AI-Result'`. */
export type LayerRole = 'base' | 'theme' | 'selection' | 'result' | 'analysis'

export type LayerSource =
  | { kind: 'geojson'; features: GeoJsonFeature[] }
  | { kind: 'geojson-collection'; collection: FeatureCollection }
  | { kind: 'osm'; city: string; key: string }

/**
 * Semantic styling only. The adapter decides how this maps onto deck.gl
 * props; the core never sees a `GeoJsonLayer`.
 */
export interface LayerStyle {
  color: RGBAColor
  radius?: number
  lineWidth?: number
  filled?: boolean
  stroked?: boolean
}

export interface LayerSpec {
  id: string
  role: LayerRole
  source: LayerSource
  style: LayerStyle
  visible: boolean
  opacity: number
  /** UI paint order, top first (mirrors the historical LayerGroup array). */
  order: number
  /**
   * Data/style change counter. Adapters rebuild a deck.gl layer only when
   * this changes, which is the performance-critical part of reconciliation.
   */
  revision: number
}

export interface ViewportSnapshot {
  center: [number, number]
  zoom: number
  bearing: number
  pitch: number
}

export type ThemeId = 'light' | 'dark'

export interface SceneState {
  layers: Record<string, LayerSpec>
  order: string[]
  selection: GeoJsonFeature | null
  hover: GeoJsonFeature | null
  viewport: ViewportSnapshot
  theme: ThemeId
  /** Set by `fitBounds` commands; the shell consumes and clears it. */
  pendingFit: BBox | null
}

export const DEFAULT_VIEWPORT: ViewportSnapshot = {
  center: [114.101275961, 22.50870175],
  zoom: 16,
  bearing: 0,
  pitch: 0,
}

export function createEmptyScene(theme: ThemeId = 'light'): SceneState {
  return {
    layers: {},
    order: [],
    selection: null,
    hover: null,
    viewport: { ...DEFAULT_VIEWPORT, center: [...DEFAULT_VIEWPORT.center] },
    theme,
    pendingFit: null,
  }
}

/** Resolve a feature list from any of the supported source kinds. */
export function sourceFeatures(source: LayerSource): GeoJsonFeature[] {
  switch (source.kind) {
    case 'geojson':
      return source.features
    case 'geojson-collection':
      return source.collection.features
    case 'osm':
      return []
  }
}
