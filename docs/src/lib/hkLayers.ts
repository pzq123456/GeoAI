/** Lazy-loaded config for the extra Hong Kong open-data layers.
 *
 * The datasets are several MB of JSON. Loading them with static imports would
 * inline all of them into the main JS bundle. `import.meta.glob` without
 * `eager: true` lets Vite emit one small chunk per layer, fetched only when the
 * scene is seeded (and cached by the browser afterwards).
 */
import type { FeatureCollection } from '@/types'
import { StaticGeoDataProvider, type JsonLoader } from '@/adapters/geo/StaticGeoDataProvider'

export interface HkLayerConfig {
  id: string
  label: string
  data: FeatureCollection
  bbox: [number, number, number, number]
  palette: [number, number, number, number][]
}

const dataLoaders = import.meta.glob('../../../data/hk-*.json') as Record<string, JsonLoader>
const metaLoaders = import.meta.glob('../../../data/meta/hk-*.meta.json') as Record<string, JsonLoader>
const provider = new StaticGeoDataProvider(dataLoaders, metaLoaders)

const LAYER_DEFS: { theme: string; label: string }[] = [
  { theme: 'environment', label: 'HK Environment 环境' },
  { theme: 'health', label: 'HK Health 医疗' },
  { theme: 'education', label: 'HK Education 教育' },
  { theme: 'sports', label: 'HK Sports 体育' },
  { theme: 'services', label: 'HK Services 公共服务' },
  { theme: 'wifi', label: 'HK Wi-Fi 热点' },
]

const PALETTES: Record<string, [number, number, number, number][]> = {
  environment: [
    [26, 145, 190, 220],
    [80, 160, 90, 220],
    [220, 140, 60, 220],
    [150, 90, 180, 220],
    [60, 170, 170, 220],
    [200, 90, 90, 220],
    [120, 120, 200, 220],
  ],
  health: [
    [225, 70, 70, 225],
    [240, 130, 90, 225],
    [200, 90, 130, 225],
    [190, 60, 100, 225],
    [230, 110, 150, 225],
    [170, 80, 140, 225],
  ],
  education: [
    [70, 120, 210, 225],
    [90, 150, 220, 225],
    [60, 100, 180, 225],
    [110, 170, 225, 225],
    [80, 135, 195, 225],
    [130, 180, 230, 225],
    [100, 115, 205, 225],
    [140, 160, 220, 225],
    [75, 145, 200, 225],
  ],
  sports: [
    [245, 150, 40, 225],
    [230, 180, 60, 225],
    [60, 170, 130, 225],
    [80, 190, 160, 225],
    [120, 180, 80, 225],
    [200, 160, 70, 225],
    [50, 180, 200, 225],
    [90, 200, 190, 225],
    [220, 120, 70, 225],
    [180, 130, 200, 225],
    [210, 190, 120, 225],
  ],
  services: [
    [140, 100, 190, 225],
    [160, 120, 205, 225],
    [120, 90, 175, 225],
    [175, 140, 215, 225],
    [130, 115, 185, 225],
    [150, 130, 200, 225],
    [115, 105, 170, 225],
    [165, 145, 210, 225],
    [135, 125, 195, 225],
  ],
  wifi: [[40, 170, 220, 210]],
}

/** Fetch the six themed layers on demand; safe to call more than once. */
export async function loadHkLayers(): Promise<HkLayerConfig[]> {
  const configs = await Promise.all(
    LAYER_DEFS.map(async ({ theme, label }) => {
      const [data, meta] = await Promise.all([
        provider.loadFeatureCollection(`hk-${theme}.json`),
        provider.loadMeta(`hk-${theme}.meta.json`),
      ])
      if (!data || !meta) return null
      return {
        id: `hk-${theme}-Layer`,
        label,
        data,
        bbox: meta.bbox,
        palette: PALETTES[theme] ?? [[140, 150, 165, 210]],
      } satisfies HkLayerConfig
    }),
  )
  return configs.filter((config): config is HkLayerConfig => config !== null)
}

/** Stable colour per category so the same facility type looks the same everywhere. */
export function hkColor(layer: HkLayerConfig, category: string): [number, number, number, number] {
  let hash = 0
  for (let i = 0; i < category.length; i += 1) {
    hash = (hash * 31 + category.charCodeAt(i)) | 0
  }
  return layer.palette[Math.abs(hash) % layer.palette.length]
}
