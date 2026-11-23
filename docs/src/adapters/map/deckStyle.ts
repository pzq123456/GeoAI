/** Semantic LayerStyle/role → deck.gl GeoJsonLayer props. */

import type { LayerRole, LayerStyle, RGBAColor } from '@/core'

export type DeckProps = Record<string, unknown>

/** Stable palette per singleton role (no magic strings outside core). */
export const ROLE_COLOR: Partial<Record<LayerRole, RGBAColor>> = {
  selection: [255, 12, 0, 255],
  result: [255, 140, 66, 180],
}

export function styleToDeckProps(style: LayerStyle, opacity = 1): DeckProps {
  return {
    opacity,
    filled: style.filled ?? true,
    stroked: style.stroked ?? true,
    getFillColor: style.color,
    getLineColor: style.color,
    lineWidthUnits: 'pixels',
    getLineWidth: style.lineWidth ?? 1,
    pointRadiusUnits: 'pixels',
    getPointRadius: style.radius ?? 5,
    pointRadiusMinPixels: 3,
    pointRadiusMaxPixels: 12,
  }
}

/** Props for a fresh singleton layer produced by `resultToLayer`. */
export function resultDeckProps(): DeckProps {
  return {
    getFillColor: ROLE_COLOR.result,
    getLineColor: [255, 255, 255, 255],
    lineWidthUnits: 'pixels',
    lineWidthMinPixels: 2,
    pointRadiusUnits: 'pixels',
    pointRadiusMinPixels: 8,
    pickable: true,
    autoHighlight: true,
  }
}
