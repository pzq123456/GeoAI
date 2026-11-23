import { defineStore } from 'pinia'
import { markRaw, reactive, ref, shallowRef } from 'vue'
import type { Map as MapLibreMap, LngLatBoundsLike, FitBoundsOptions } from 'maplibre-gl'
import type { MapboxOverlay } from '@deck.gl/mapbox'
import {
  createEmptyScene,
  sceneReducer,
  type BBox,
  type FitBoundsOptions as CoreFitBoundsOptions,
  type FlyToTarget,
  type GeoJsonFeature,
  type SceneCommand,
  type SceneState,
} from '@/core'
import { MapLibreRenderer } from '@/adapters/map/MapLibreRenderer'
import { buildScene } from '@/adapters/map/layerSpec'
import { LayerGroup, type LayerItem } from '@/composables/useLayerGroup'
import { applyTheme, mapThemeFor, type ThemeId } from '@/lib/mapTheme'

/** Convert MapLibre's permissive bounds input into a core BBox. */
function toBBox(bounds: LngLatBoundsLike): BBox | null {
  if (Array.isArray(bounds)) {
    if (bounds.length === 4 && typeof bounds[0] === 'number') {
      return [bounds[0], bounds[1], bounds[2], bounds[3]] as BBox
    }
    if (Array.isArray(bounds[0]) && bounds.length === 2) {
      const [west, south] = bounds[0] as [number, number]
      const [east, north] = bounds[1] as [number, number]
      return [west, south, east, north]
    }
  }
  const b = bounds as { getWest?: () => number; getSouth?: () => number; getEast?: () => number; getNorth?: () => number }
  if (typeof b.getWest === 'function' && typeof b.getNorth === 'function') {
    return [b.getWest!(), b.getSouth!(), b.getEast!(), b.getNorth!()]
  }
  return null
}

export const useMapStore = defineStore('map', () => {
  // ---------------------------------------------------------------- domain
  const hoveredRegion = ref<GeoJsonFeature | null>(null)
  const selectedRegion = ref<GeoJsonFeature | null>(null)

  // --------------------------------------------------------------- runtime
  // MapLibre/deck.gl instances stay out of Vue's deep reactivity.
  const map = shallowRef<MapLibreMap | null>(null)
  const overlay = shallowRef<MapboxOverlay | null>(null)
  const loaded = ref(false)
  const loading = ref(true)
  const error = ref<string | null>(null)
  const viewport = reactive({
    center: [114.101275961, 22.50870175] as [number, number],
    zoom: 16,
    bearing: 0,
    pitch: 0,
  })

  // ----------------------------------------------------------------- scene
  // The LayerGroup remains the live UI registry (the .vue panel mutates Layer
  // instances directly). `scene` is its serialisable core mirror; the renderer
  // reconciles the two by revision.
  const layers = new LayerGroup()
  const renderer = new MapLibreRenderer()
  const scene = ref<SceneState>(createEmptyScene())
  let prevScene: SceneState | null = null

  const syncScene = () => {
    const next = buildScene({
      layers: layers.layers,
      selection: selectedRegion.value,
      hover: hoveredRegion.value,
      viewport: {
        center: [...viewport.center] as [number, number],
        zoom: viewport.zoom,
        bearing: viewport.bearing,
        pitch: viewport.pitch,
      },
      theme: scene.value.theme,
    })
    prevScene = scene.value
    scene.value = next
    if (loaded.value) renderer.reconcile(next, prevScene)
  }

  /** Apply a core scene command, mirroring it into the legacy UI registry. */
  const dispatch = (cmd: SceneCommand) => {
    scene.value = sceneReducer(scene.value, cmd)
    switch (cmd.type) {
      case 'setLayerVisibility':
        layers.setVisibility(cmd.id, cmd.visible)
        break
      case 'setLayerOpacity':
        layers.setOpacity(cmd.id, cmd.opacity)
        break
      case 'selectFeature': {
        const highlight = layers.layers.find(
          (layer) => layer.role === 'selection' || layer.id === 'Highlight-Layer',
        )
        if (highlight) highlight.setData(cmd.feature ? [cmd.feature] : [])
        break
      }
      default:
        break
    }
    syncScene()
  }

  const syncViewport = () => {
    const instance = map.value
    if (!instance) return
    const c = instance.getCenter()
    viewport.center = [c.lng, c.lat]
    viewport.zoom = instance.getZoom()
    viewport.bearing = instance.getBearing()
    viewport.pitch = instance.getPitch()
    syncScene()
  }

  /** Push the current scene into the deck.gl overlay (incremental by revision). */
  const refreshDeck = () => {
    syncScene()
  }

  const attach = (instance: MapLibreMap) => {
    map.value = markRaw(instance)
    renderer.attach(instance, () => layers.getLayers() as unknown as { id: string }[])
    overlay.value = markRaw(renderer.getOverlay()!)
    loaded.value = true
    loading.value = false
    error.value = null
    instance.on('moveend', syncViewport)
    syncViewport()
    syncScene()
  }

  const detach = () => {
    renderer.detach()
    overlay.value = null
    map.value = null
    loaded.value = false
  }

  const flyTo = (options: Parameters<MapLibreMap['flyTo']>[0]) => {
    if (map.value && loaded.value) renderer.flyTo(options as unknown as FlyToTarget)
  }

  const fitBounds = (bounds: LngLatBoundsLike, options?: FitBoundsOptions) => {
    const bbox = toBBox(bounds)
    if (!bbox || !map.value || !loaded.value) return
    dispatch({ type: 'fitBounds', bbox })
    renderer.fitBounds(bbox, options as unknown as CoreFitBoundsOptions)
  }

  /**
   * Strategy-dispatched theme switch. Data is serialisable, so it can be
   * called from anywhere; style reloads restore the overlay + scene layers.
   */
  const setTheme = async (id: ThemeId) => {
    const instance = map.value
    if (!instance || !loaded.value) return
    dispatch({ type: 'setTheme', theme: id })

    await applyTheme(instance, mapThemeFor(id), {
      beforeReload: () => renderer.detachOverlay(),
      afterReload: () => {
        if (!map.value) return
        renderer.attach(map.value, () => layers.getLayers() as unknown as { id: string }[])
        overlay.value = markRaw(renderer.getOverlay()!)
        refreshDeck()
        syncViewport()
      },
    })
  }

  // ------------------------------------------------------------- selection
  const updateHoveredRegion = (region: GeoJsonFeature | null) => {
    hoveredRegion.value = region
    dispatch({ type: 'hoverFeature', feature: region })
  }

  const updateSelectedRegion = (region: GeoJsonFeature | null) => {
    selectedRegion.value = region
    dispatch({ type: 'selectFeature', feature: region })
  }

  // -------------------------------------------------------------- layers
  const addLayer = (layer: LayerItem) => {
    layers.addLayer(layer)
    syncScene()
  }

  const removeLayer = (id: string) => {
    layers.removeLayer(id)
    syncScene()
  }

  const setLayerOrder = (order: LayerItem[]) => {
    layers.setLayerOrder(order)
    syncScene()
  }

  const setLayerOpacity = (id: string, value: number) => {
    dispatch({ type: 'setLayerOpacity', id, opacity: value })
  }

  const setLayerVisibility = (id: string, value: boolean) => {
    dispatch({ type: 'setLayerVisibility', id, visible: value })
  }

  return {
    // domain
    hoveredRegion,
    selectedRegion,
    // runtime
    map,
    overlay,
    loaded,
    loading,
    error,
    viewport,
    // scene
    layers,
    scene,
    dispatch,
    attach,
    detach,
    refreshDeck,
    flyTo,
    fitBounds,
    setTheme,
    // selection
    updateHoveredRegion,
    updateSelectedRegion,
    // layers
    addLayer,
    removeLayer,
    setLayerOrder,
    setLayerOpacity,
    setLayerVisibility,
  }
})
