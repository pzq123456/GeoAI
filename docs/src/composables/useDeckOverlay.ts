import { MapboxOverlay } from '@deck.gl/mapbox'
import type { Map as MapLibreMap, IControl } from 'maplibre-gl'

export function useDeckOverlay(map: MapLibreMap | null): MapboxOverlay {
  const overlay = new MapboxOverlay({
    interleaved: true,
    layers: [],
  })

  if (map) {
    map.addControl(overlay as unknown as IControl)
  }

  return overlay
}

export function removeDeckOverlay(map: MapLibreMap | null, overlay: MapboxOverlay | null): void {
  if (map && overlay) {
    map.removeControl(overlay as unknown as IControl)
  }
}
