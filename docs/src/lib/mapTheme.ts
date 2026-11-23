import type { Map as MapLibreMap } from 'maplibre-gl'
import type { ThemeId as CoreThemeId } from '@/core'

/** Theme id now lives in the core scene model; re-export keeps callers intact. */
export type ThemeId = CoreThemeId

/**
 * A theme is a descriptor, not a hardcoded `setStyle()` call.
 *
 * - `paint`   — only colours/opacity changed: patch in place, no scene loss.
 * - `source`  — data changed but the layer tree is stable: patch sources.
 * - `style`   — full basemap swap: reload, then let the caller restore the
 *               deck.gl overlay, scene layers and layer-scoped event handlers.
 */
export type ThemeStrategy = 'paint' | 'source' | 'style'

export interface PaintOverride {
  layerId: string
  props: Record<string, unknown>
}

export interface SourceOverride {
  id: string
  data: unknown
}

export interface MapTheme {
  id: ThemeId
  strategy: ThemeStrategy
  styleUrl?: string
  paint?: PaintOverride[]
  sources?: SourceOverride[]
}

const BASEMAP_STYLE: Record<ThemeId, string> = {
  light: 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
  dark: 'https://basemaps.cartocdn.com/gl/dark-matter-nolabels-gl-style/style.json',
}

/**
 * Resolve the theme for the current UI mode.
 *
 * Today light/dark are two different CARTO style documents, so the `style`
 * strategy is selected. If the basemap is later expressed as one style with
 * themeable paint properties, switch this to `paint` without touching callers.
 */
export function mapThemeFor(id: ThemeId): MapTheme {
  return { id, strategy: 'style', styleUrl: BASEMAP_STYLE[id] }
}

export interface ThemeHooks {
  /** Tear down anything attached to the old style (e.g. deck.gl overlay). */
  beforeReload?: () => void
  /** Re-attach scene state after the new style has loaded. */
  afterReload?: () => void | Promise<void>
}

export async function applyTheme(
  map: MapLibreMap,
  theme: MapTheme,
  hooks: ThemeHooks = {},
): Promise<void> {
  if (theme.strategy === 'paint') {
    for (const override of theme.paint ?? []) {
      if (!map.getLayer(override.layerId)) continue
      for (const [prop, value] of Object.entries(override.props)) {
        map.setPaintProperty(override.layerId, prop as never, value as never)
      }
    }
    return
  }

  if (theme.strategy === 'source') {
    for (const override of theme.sources ?? []) {
      const source = map.getSource(override.id) as { setData?: (data: unknown) => void } | undefined
      source?.setData?.(override.data)
    }
    return
  }

  if (!theme.styleUrl) return

  hooks.beforeReload?.()
  // Subscribe BEFORE setStyle: a cached style can finish loading before a
  // listener attached afterwards would ever see the event.
  const styleLoaded = new Promise<void>((resolve) => {
    map.once('style.load', () => resolve())
  })
  map.setStyle(theme.styleUrl)
  await styleLoaded
  await hooks.afterReload?.()
}
