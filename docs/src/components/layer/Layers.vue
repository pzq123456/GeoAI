<!-- docs/src/components/layer/Layers.vue -->
<template>
  <div class="flex min-h-0 flex-col overflow-hidden rounded-xl border border-border bg-surface-2">
    <LayerHeader
      :layers="mapStore.layers.layers"
      :is-layer-list-visible="isLayerListVisible"
      @toggle-all-details="toggleAllDetails"
      @toggle-layer-list="toggleLayerList"
    />

    <div
      ref="el"
      v-show="isLayerListVisible"
      class="flex max-h-[240px] flex-col gap-1.5 overflow-y-auto bg-surface-solid p-2"
    >
      <LayerCard
        v-for="layer in mapStore.layers.layers"
        :key="layer.id"
        :layer="layer"
        @toggle-expand="toggleExpand"
        @toggle-visibility="toggleVisibility"
        @remove-layer="handleRemoveLayer"
        @download-layer="handleDownloadLayer"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, toRef } from 'vue'
import { useDraggable } from 'vue-draggable-plus'
import type { LayerItem } from '@/composables/useLayerGroup'
import { useMapStore } from '@/stores/mapStore'

import LayerHeader from './LayerHeader.vue'
import LayerCard from './LayerCard.vue'

const mapStore = useMapStore()
const isLayerListVisible = ref(true)

const toggleExpand = (id: string) => {
  const layer = mapStore.layers.layers.find((item) => item.id === id)
  if (layer) layer.isExpanded = !layer.isExpanded
}

const toggleVisibility = (layer: LayerItem) => {
  mapStore.setLayerVisibility(layer.id, !layer.visible)
}

const handleRemoveLayer = (id: string) => {
  mapStore.removeLayer(id)
}

const handleDownloadLayer = (layer: LayerItem) => {
  const data = layer.data?.features || layer.data
  if (!data) return
  const blob = new Blob([JSON.stringify(data)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${layer.id}.geojson`
  a.click()
  URL.revokeObjectURL(url)
}

const toggleLayerList = () => {
  isLayerListVisible.value = !isLayerListVisible.value
}

const toggleAllDetails = () => {
  const allExpanded = mapStore.layers.layers.every((layer) => layer.isExpanded)
  mapStore.layers.layers.forEach((layer) => {
    layer.isExpanded = !allExpanded
  })
}

const el = ref<HTMLElement | null>(null)
useDraggable(el, toRef(mapStore.layers, 'layers'), {
  animation: 150,
  handle: '.drag-handle',
  onUpdate: () => mapStore.refreshDeck(),
})
</script>
