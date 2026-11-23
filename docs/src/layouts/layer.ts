import { Layer } from '@/composables/useLayerGroup'
import type { LayerConstructor } from '@/composables/useLayer'
import type { LayerRole } from '@/core'
import { GeoJsonLayer } from '@deck.gl/layers'
import { HK_GREEN_COLORS, hkGreenSpace } from '@/lib/greenSpace'
import { hkDistricts } from '@/lib/hkDistricts'
import { hkColor, type HkLayerConfig } from '@/lib/hkLayers'
import { useMapStore } from '@/stores/mapStore'
import type { FeatureCollection, GeoJsonFeature } from '@/types'

// The legacy tree inventory is optional. A glob keeps the build working while
// data/tree.json is absent and restores the layer automatically if it returns.
const treeModules = import.meta.glob('../../../data/tree.json', { eager: true }) as Record<
  string,
  { default: FeatureCollection }
>
const treeData = Object.values(treeModules)[0]?.default

/**
 * Layer factories only. The registry itself lives in the Pinia scene store,
 * so no module can silently mutate it from outside the UI/agent boundary.
 */
export function createInitialLayers(): Layer[] {
  const treeLayer = new Layer('tree-Layer', GeoJsonLayer as unknown as LayerConstructor, {
    role: 'base' as LayerRole,
    opacity: 0.5,
    visible: true,
    props: {
      lineWidthMinPixels: 2,
      getLineColor: [128, 128, 128],
      getFillColor: [0, 25, 18, 10],
      pickable: true,
      onClick: (info: { object?: GeoJsonFeature | null }) => {
        if (!info.object) return
        // Resolve lazily: this factory runs before Pinia is installed.
        useMapStore().updateSelectedRegion(info.object)
      },
    },
    // treeData is undefined while the legacy tree inventory is absent.
    data: treeData?.features ?? [],
  })

  const highlightLayer = new Layer('Highlight-Layer', GeoJsonLayer as unknown as LayerConstructor, {
    role: 'selection' as LayerRole,
    opacity: 0.8,
    visible: true,
    props: {
      data: [],
      lineWidthMinPixels: 12,
      getLineColor: [255, 12, 0, 255],
      getFillColor: [255, 23, 0, 100],
      pickable: false,
    },
  })

  const greenLayer = new Layer('hk-green-space-Layer', GeoJsonLayer as unknown as LayerConstructor, {
    role: 'theme' as LayerRole,
    opacity: 0.9,
    visible: true,
    props: {
      pickable: true,
      autoHighlight: true,
      highlightColor: [255, 255, 255, 120],
      pointRadiusUnits: 'pixels',
      pointRadiusMinPixels: 4,
      pointRadiusMaxPixels: 12,
      getPointRadius: (feature: GeoJsonFeature) =>
        feature.properties.category === 'country_park' ? 7 : 5,
      getFillColor: (feature: GeoJsonFeature) =>
        HK_GREEN_COLORS[String(feature.properties.category)] ?? [140, 150, 165, 210],
      stroked: true,
      lineWidthUnits: 'pixels',
      getLineWidth: 1,
      getLineColor: [255, 255, 255, 180],
      onClick: (info: { object?: GeoJsonFeature | null }) => {
        if (!info.object) return
        useMapStore().updateSelectedRegion(info.object)
      },
    },
    data: hkGreenSpace.features,
  })

  const districtLayer = new Layer('hk-districts-Layer', GeoJsonLayer as unknown as LayerConstructor, {
    role: 'theme' as LayerRole,
    opacity: 0.7,
    visible: true,
    props: {
      filled: true,
      stroked: true,
      getFillColor: [46, 160, 67, 22],
      getLineColor: [120, 200, 140, 150],
      lineWidthUnits: 'pixels',
      getLineWidth: 1,
      pickable: true,
      autoHighlight: true,
      highlightColor: [255, 255, 255, 70],
      onClick: (info: { object?: GeoJsonFeature | null }) => {
        if (!info.object) return
        useMapStore().updateSelectedRegion(info.object)
      },
    },
    data: hkDistricts.features,
  })

  // LayerGroup reverses this list before deck.gl: districts paint first
  // (bottom), the selection highlight last (top).
  return [
    highlightLayer,
    greenLayer,
    ...(treeData ? [treeLayer] : []),
    districtLayer,
  ]
}

/** Build one lazily-loaded theme layer (called after its JSON chunk arrives). */
export function createHkLayer(cfg: HkLayerConfig): Layer {
  return new Layer(cfg.id, GeoJsonLayer as unknown as LayerConstructor, {
    role: 'theme' as LayerRole,
    opacity: 0.85,
    visible: false, // opt-in via the layer panel; avoids cluttering the map
    props: {
      pickable: true,
      autoHighlight: true,
      highlightColor: [255, 255, 255, 90],
      pointRadiusUnits: 'pixels',
      pointRadiusMinPixels: 3,
      pointRadiusMaxPixels: 9,
      getPointRadius: () => (cfg.id === 'hk-wifi-Layer' ? 3 : 5),
      getFillColor: (feature: GeoJsonFeature) => hkColor(cfg, String(feature.properties.category)),
      stroked: true,
      lineWidthUnits: 'pixels',
      getLineWidth: 1,
      getLineColor: [255, 255, 255, 170],
      onClick: (info: { object?: GeoJsonFeature | null }) => {
        if (!info.object) return
        useMapStore().updateSelectedRegion(info.object)
      },
    },
    data: cfg.data.features,
  })
}
