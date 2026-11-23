/** GeoDataProvider backed by lazily-imported static JSON chunks. */

import { isFeatureCollection, type GeoDataProvider, type BBox } from '@/core'

export type JsonLoader = () => Promise<{ default: unknown }>

export class StaticGeoDataProvider implements GeoDataProvider {
  constructor(
    private readonly dataLoaders: Record<string, JsonLoader> = {},
    private readonly metaLoaders: Record<string, JsonLoader> = {},
  ) {}

  private loaderFor(loaders: Record<string, JsonLoader>, key: string): JsonLoader | undefined {
    return Object.entries(loaders).find(([path]) => path.includes(key))?.[1]
  }

  async loadFeatureCollection(key: string) {
    const loader = this.loaderFor(this.dataLoaders, key)
    if (!loader) return null
    const module = await loader()
    return isFeatureCollection(module.default) ? module.default : null
  }

  async loadMeta(key: string): Promise<{ bbox: BBox } | null> {
    const loader = this.loaderFor(this.metaLoaders, key)
    if (!loader) return null
    const module = await loader()
    const meta = module.default as { bbox?: number[] }
    if (!Array.isArray(meta?.bbox) || meta.bbox.length !== 4) return null
    return { bbox: meta.bbox as BBox }
  }
}
