/**
 * Ports (interfaces) at the core/adapters boundary.
 *
 * Everything here is structural TypeScript: no framework imports, so a
 * different shell (Web Worker test, alternate map engine, alternate transport)
 * can implement the same contracts.
 */

import type { AgentEvent, AgentRequest } from './model/agent'
import type { BBox, FeatureCollection, GeoJsonFeature } from './model/geo'
import type { SceneState, ViewportSnapshot } from './model/scene'

export type Unsubscribe = () => void

/** Camera target accepted by `MapRenderer.flyTo`. */
export interface FlyToTarget {
  center: [number, number]
  zoom?: number
  bearing?: number
  pitch?: number
  duration?: number
  padding?: number
}

export interface FitBoundsOptions {
  padding?: number
  duration?: number
}

export interface MapRenderer {
  /** Diff `next` against `prev`; rebuild only layers whose revision changed. */
  reconcile(next: SceneState, prev: SceneState | null): void
  flyTo(target: FlyToTarget): void
  fitBounds(bbox: BBox, options?: FitBoundsOptions): void
  onFeatureClick(cb: (feature: GeoJsonFeature) => void): Unsubscribe
}

export interface AgentTransport {
  stream(req: AgentRequest): AsyncIterable<AgentEvent>
  abort(): void
}

export interface GeoDataProvider {
  /** Lazily resolve a named static/demo dataset. */
  loadFeatureCollection(key: string): Promise<FeatureCollection | null>
  /** Resolve metadata (bbox, palette, ...) for a named dataset. */
  loadMeta(key: string): Promise<{ bbox: BBox } | null>
}
