<template>
  <div ref="mapContainerRef" class="absolute inset-0 h-full w-full border-0">
    <div class="pointer-events-none absolute inset-0 z-[1]">
      <div class="pointer-events-auto absolute bottom-3.5 right-3.5 overflow-hidden rounded-xl">
        <slot name="legend"></slot>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import * as maplibregl from 'maplibre-gl'
import type { Map as MapLibreMap, FlyToOptions, LngLatBoundsLike, FitBoundsOptions } from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { isDark } from '@/composables/useTheme'
import { mapThemeFor } from '@/lib/mapTheme'
import { useMapStore } from '@/stores/mapStore'

/** Geometry props are initial values only; later camera moves go through the store. */
const props = withDefaults(
  defineProps<{
    center?: [number, number]
    zoom?: number
    bearing?: number
    pitch?: number
  }>(),
  {
    center: () => [114.101275961, 22.50870175],
    zoom: 16,
    bearing: 0,
    pitch: 0,
  },
)

const emit = defineEmits<{
  'map-loaded': [map: MapLibreMap]
  'map-click': [payload: { lngLat: maplibregl.LngLat; point: { x: number; y: number } }]
  'map-move': [state: { center: maplibregl.LngLat; zoom: number; bearing: number; pitch: number }]
}>()

const mapStore = useMapStore()
const mapContainerRef = ref<HTMLDivElement | null>(null)
let instance: MapLibreMap | null = null
let initialized = false

onMounted(() => {
  if (initialized || !mapContainerRef.value) return
  initialized = true

  const initialTheme = mapThemeFor(isDark.value ? 'dark' : 'light')
  instance = new maplibregl.Map({
    container: mapContainerRef.value,
    style: initialTheme.styleUrl!,
    center: props.center,
    zoom: props.zoom,
    bearing: props.bearing,
    pitch: props.pitch,
    attributionControl: { compact: true },
    canvasContextAttributes: { antialias: true, preserveDrawingBuffer: true },
  })

  // Unreachable tiles degrade to console noise — the map still boots.
  instance.on('error', (e) => console.warn('[map]', e.error?.message ?? e))

  instance.on('load', () => {
    if (!instance) return
    mapStore.attach(instance)
    emit('map-loaded', instance)
  })

  instance.on('click', (e) => {
    emit('map-click', { lngLat: e.lngLat, point: e.point })
  })

  instance.on('moveend', () => {
    if (!instance) return
    emit('map-move', {
      center: instance.getCenter(),
      zoom: instance.getZoom(),
      bearing: instance.getBearing(),
      pitch: instance.getPitch(),
    })
  })
})

watch(isDark, (dark) => {
  void mapStore.setTheme(dark ? 'dark' : 'light')
})

onUnmounted(() => {
  mapStore.detach()
  instance?.remove()
  instance = null
})

defineExpose({
  flyTo: (options: FlyToOptions) => mapStore.flyTo(options),
  fitBounds: (bounds: LngLatBoundsLike, options?: FitBoundsOptions) => mapStore.fitBounds(bounds, options),
})
</script>
