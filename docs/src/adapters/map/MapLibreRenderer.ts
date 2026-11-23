/**
 * MapRenderer adapter. Owns the MapLibre + MapboxOverlay instance that used to
 * live inside the Pinia store, and performs revision-based reconciliation:
 * deck.gl layer instances are cached by id+revision, so a refresh only
 * rebuilds the layers whose data/style actually changed.
 */

import type { Map as MapLibreMap } from 'maplibre-gl'
import type { MapboxOverlay } from '@deck.gl/mapbox'
import {
  type BBox,
  type FitBoundsOptions,
  type FlyToTarget,
  type GeoJsonFeature,
  type MapRenderer,
  type SceneState,
  type Unsubscribe,
} from '@/core'
import { removeDeckOverlay, useDeckOverlay } from '@/composables/useDeckOverlay'

type DeckLayer = { id: string } & Record<string, unknown>

export class MapLibreRenderer implements MapRenderer {
  private map: MapLibreMap | null = null
  private overlay: MapboxOverlay | null = null
  private layerProvider: () => DeckLayer[] = () => []
  private clickHandlers = new Set<(feature: GeoJsonFeature) => void>()
  private clickBound = false

  /** Attach to a MapLibre instance and register the source of deck layers. */
  attach(map: MapLibreMap, layerProvider: () => DeckLayer[]): void {
    this.detach()
    this.map = map
    this.layerProvider = layerProvider
    this.overlay = useDeckOverlay(map)
    this.overlay.setProps({ layers: [] })
  }

  /** Tear down only the overlay; the MapLibre instance survives style reloads. */
  detachOverlay(): void {
    if (this.map && this.overlay) removeDeckOverlay(this.map, this.overlay)
    this.overlay = null
  }

  detach(): void {
    this.detachOverlay()
    this.map = null
    this.layerProvider = () => []
  }

  getOverlay(): MapboxOverlay | null {
    return this.overlay
  }

  /**
   * Hand a fresh list of layer descriptors to deck.gl on every change.
   *
   * deck.gl performs its own id-based diffing and instance reuse. We must NOT
   * cache deck.gl layer instances ourselves: deck.gl finalizes (destroys) an
   * instance when its id leaves the array, and reusing such an instance throws
   * "finalized layer cannot be reused", which crashes the whole overlay.
   * Visibility is a normal prop, so hidden layers stay in the array with
   * `visible: false` and are never destroyed.
   */
  reconcile(next: SceneState, _prev: SceneState | null): void {
    if (!this.overlay) return

    const fresh = this.layerProvider()
    // Only drop layers that no longer exist in the scene at all. Hidden layers
    // remain in `fresh` with visible:false, which deck.gl handles natively.
    const nextLayers = fresh.filter((layer) => Boolean(next.layers[layer.id]))

    this.overlay.setProps({ layers: nextLayers as never })
  }

  flyTo(target: FlyToTarget): void {
    if (target.center) {
      this.map?.flyTo({
        center: target.center,
        zoom: target.zoom,
        bearing: target.bearing,
        pitch: target.pitch,
        duration: target.duration,
        padding: target.padding,
      } as never)
    }
  }

  fitBounds(bbox: BBox, options: FitBoundsOptions = {}): void {
    const [west, south, east, north] = bbox
    this.map?.fitBounds(
      [
        [west, south],
        [east, north],
      ],
      { padding: 70, duration: 1000, ...options } as never,
    )
  }

  /** Subscribe to deck.gl pick events via MapLibre's click + overlay picking. */
  onFeatureClick(cb: (feature: GeoJsonFeature) => void): Unsubscribe {
    this.clickHandlers.add(cb)
    if (!this.clickBound && this.map && this.overlay) {
      this.clickBound = true
      this.map.on('click', (event) => {
        const picked = (this.overlay as unknown as {
          pickObject?: (opts: { x: number; y: number; radius: number }) => { object?: GeoJsonFeature } | null
        }).pickObject?.({ x: event.point.x, y: event.point.y, radius: 4 })
        if (picked?.object) this.emitClick(picked.object)
      })
    }
    return () => this.clickHandlers.delete(cb)
  }

  private emitClick(feature: GeoJsonFeature): void {
    for (const cb of this.clickHandlers) cb(feature)
  }
}
