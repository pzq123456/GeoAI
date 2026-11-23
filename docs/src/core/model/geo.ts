/**
 * Framework-free geometry types.
 *
 * These mirror the historical `@/types` shapes so the public frontend API is
 * unchanged, but they live in `core/` so reducers/selectors can be used from a
 * Web Worker, Node test, or any future non-Vue shell.
 */

export interface GeoJsonFeature {
  type: 'Feature'
  id?: string | number
  geometry: {
    type: string
    coordinates: unknown
  } | null
  properties: Record<string, unknown> & {
    ai_label?: string
    name?: string
    [key: string]: unknown
  }
}

export interface FeatureCollection {
  type: 'FeatureCollection'
  features: GeoJsonFeature[]
}

/** `[west, south, east, north]` */
export type BBox = [number, number, number, number]

/** deck.gl-style RGBA tuple, kept as a plain serialisable array in core. */
export type RGBAColor = [number, number, number, number]

export function isFeatureCollection(value: unknown): value is FeatureCollection {
  return (
    typeof value === 'object' &&
    value !== null &&
    (value as { type?: unknown }).type === 'FeatureCollection' &&
    Array.isArray((value as { features?: unknown }).features)
  )
}
