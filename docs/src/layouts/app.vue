<template>
  <div class="flex h-screen w-screen flex-col overflow-hidden bg-bg">
    <!-- Top bar -->
    <header class="glass z-40 mx-3.5 mt-2.5 flex h-14 shrink-0 items-center justify-between rounded-2xl px-4">
      <div class="flex min-w-[180px] items-center gap-2.5 max-sm:min-w-0">
        <div class="grid h-7 w-7 place-items-center rounded-lg bg-brand">
          <span class="h-2 w-2 rounded-full bg-white"></span>
        </div>
        <div class="flex flex-col leading-tight">
          <strong class="text-base tracking-tight">Geo<span class="gradient-text">AI</span></strong>
          <small class="text-[11px] uppercase tracking-[1px] text-text-3 max-sm:hidden">Spatial Agent Console</small>
        </div>
      </div>

      <div class="hidden flex-1 justify-center md:flex">
        <span class="rounded-full border border-border px-2.5 py-1 font-mono text-[11px] tracking-[1.2px] text-text-3">
          MAP-FIRST WORKSPACE
        </span>
      </div>

      <div class="flex items-center gap-2">
        <Button
          variant="ghost"
          size="sm"
          class="gap-1.5"
          :class="workspace.panels.layers ? 'border border-brand/30 bg-brand-soft text-brand' : ''"
          @click="workspace.togglePanel('layers')"
        >
          <LayersIcon :size="14" /><span class="max-sm:hidden">Layers</span>
        </Button>
        <Button
          variant="ghost"
          size="sm"
          class="gap-1.5"
          :class="workspace.panels.chat ? 'border border-brand/30 bg-brand-soft text-brand' : ''"
          @click="workspace.togglePanel('chat')"
        >
          <MessageSquare :size="14" /><span class="max-sm:hidden">Agent</span>
        </Button>
        <Tooltip content="Toggle theme">
          <ThemeSwitch />
        </Tooltip>
        <Tooltip content="Fullscreen">
          <Button variant="ghost" size="icon" aria-label="fullscreen" @click="handleFullScreen">
            <Maximize2 :size="15" />
          </Button>
        </Tooltip>
      </div>
    </header>

    <!-- Workspace: the map is the stage; panels float above it -->
    <main class="relative min-h-0 flex-1 overflow-hidden">
      <MapComponent
        :center="[initialViewState.longitude, initialViewState.latitude]"
        :zoom="initialViewState.zoom"
        @map-click="handleMapClick"
      >
        <template #legend>
          <div class="glass flex flex-col gap-1.5 rounded-xl px-3 py-2.5 text-xs text-text-2">
            <span class="text-[11px] font-semibold tracking-wide text-text-3">HK Green Space</span>
            <span v-for="item in HK_GREEN_LEGEND" :key="item.category" class="flex items-center gap-1.5 whitespace-nowrap">
              <i :style="{ background: item.color }" class="h-2 w-2 shrink-0 rounded-full"></i>{{ item.label }}
            </span>
            <Button
              variant="outline"
              size="sm"
              class="mt-0.5 h-6 w-full justify-center text-[11px]"
              @click="fitHongKong"
            >全港概览</Button>
            <Button
              variant="outline"
              size="sm"
              class="mt-0.5 h-6 w-full justify-center text-[11px]"
              :class="districtsVisible ? 'border-brand bg-brand text-white hover:bg-brand/90' : ''"
              @click="toggleDistricts"
            >区界 {{ districtsVisible ? '开' : '关' }}</Button>
          </div>
        </template>
      </MapComponent>

      <!-- Context-aware interaction: selection is surfaced and fed to the agent -->
      <div
        v-if="selectedRegion"
        class="glass absolute left-1/2 top-3.5 z-[15] flex max-w-[min(46vw,460px)] -translate-x-1/2 items-center gap-2.5 rounded-xl py-2 pl-3 pr-2.5 max-sm:top-2 max-sm:max-w-[calc(100vw-24px)]"
      >
        <span class="h-2 w-2 shrink-0 rounded-full bg-brand"></span>
        <div class="flex min-w-0 flex-col leading-tight">
          <strong class="truncate text-xs">{{ selectedName }}</strong>
          <small class="text-[11px] text-text-3">已选中 · 已加入 Agent Context</small>
        </div>
        <Button size="sm" class="h-7 shrink-0 gap-1 text-[11px]" @click="askAboutSelection">
          分析选中对象 <ArrowRight :size="12" />
        </Button>
        <button
          type="button"
          title="清除选择"
          class="shrink-0 border-0 bg-transparent text-text-3 transition-colors hover:text-text"
          @click="mapStore.updateSelectedRegion(null)"
        >
          <X :size="14" />
        </button>
      </div>

      <!-- Left floating panel -->
      <aside
        class="glass absolute bottom-3.5 left-3.5 top-3.5 z-20 flex min-h-0 flex-col overflow-hidden rounded-2xl transition-[width,height] duration-200"
        :class="workspace.panels.layers
          ? 'w-[286px] max-lg:w-[230px] max-sm:inset-x-2 max-sm:bottom-2 max-sm:top-auto max-sm:h-[52vh] max-sm:w-auto'
          : 'w-10 max-sm:inset-x-2 max-sm:bottom-2 max-sm:top-auto max-sm:h-11 max-sm:w-auto'"
      >
        <button
          type="button"
          class="absolute z-[2] grid h-6 w-6 place-items-center rounded-lg border border-border bg-surface-2 text-text-2 transition-colors hover:text-brand"
          :title="workspace.panels.layers ? '收起' : '展开'"
          :class="workspace.panels.layers ? 'right-2.5 top-3' : 'right-2 top-1/2 -translate-y-1/2'"
          @click="workspace.togglePanel('layers')"
        >
          <ChevronLeft v-if="workspace.panels.layers" :size="13" />
          <LayersIcon v-else :size="13" />
        </button>

        <div v-show="workspace.panels.layers" class="flex min-h-0 flex-1 flex-col gap-3 overflow-hidden px-3.5 pb-2.5 pt-4">
          <div class="h-px shrink-0 bg-border"></div>

          <section class="flex min-h-0 flex-col gap-2.5">
            <div class="flex items-center gap-2.5 pr-6">
              <div class="grid h-7 w-7 shrink-0 place-items-center rounded-lg bg-brand-soft text-brand">
                <LayersIcon :size="14" />
              </div>
              <div>
                <h3 class="text-sm font-semibold">Layers</h3>
                <small class="text-[11px] text-text-3">Map sources</small>
              </div>
            </div>
            <Layers />
          </section>

          <div class="h-px shrink-0 bg-border"></div>

          <section class="flex min-h-0 flex-1 flex-col gap-2.5 overflow-y-auto">
            <div class="flex items-center gap-2.5 pr-6">
              <div class="grid h-7 w-7 shrink-0 place-items-center rounded-lg bg-brand-soft text-brand">
                <Settings2 :size="14" />
              </div>
              <div>
                <h3 class="text-sm font-semibold">Inspector</h3>
                <small class="text-[11px] text-text-3">Selected feature</small>
              </div>
              <Button
                v-if="selectedRegion"
                variant="outline"
                size="sm"
                class="ml-auto h-6 px-2 text-[11px]"
                @click="askAboutSelection"
              >Ask AI</Button>
            </div>
            <PropertyCard :data="selectedRegion" />
          </section>
        </div>

        <div v-show="workspace.panels.layers" class="flex shrink-0 items-center gap-1.5 border-t border-border px-3.5 pb-2.5 pt-2 text-[11px] text-text-3">
          <span class="h-1.5 w-1.5 rounded-full bg-brand"></span>
          <span>GIS engine ready</span>
        </div>
      </aside>

      <!-- Right floating panel -->
      <aside
        class="glass absolute bottom-3.5 right-3.5 top-3.5 z-20 flex min-h-0 flex-col overflow-hidden rounded-2xl transition-[width,height] duration-200"
        :class="workspace.panels.chat
          ? 'w-[560px] max-xl:w-[480px] max-lg:w-[400px] max-sm:inset-x-2 max-sm:bottom-2 max-sm:top-auto max-sm:h-[64vh] max-sm:w-auto'
          : 'w-10 max-sm:inset-x-2 max-sm:bottom-2 max-sm:top-auto max-sm:h-11 max-sm:w-auto'"
      >
        <button
          type="button"
          class="absolute z-[2] grid h-6 w-6 place-items-center rounded-lg border border-border bg-surface-2 text-text-2 transition-colors hover:text-brand"
          :title="workspace.panels.chat ? '收起' : '展开'"
          :class="workspace.panels.chat ? 'left-2 top-3' : 'left-2 top-1/2 -translate-y-1/2'"
          @click="workspace.togglePanel('chat')"
        >
          <ChevronRight v-if="workspace.panels.chat" :size="13" />
          <MessageSquare v-else :size="13" />
        </button>
        <AIChat v-show="workspace.panels.chat" class="min-h-0 flex-1" @refresh-map="mapStore.refreshDeck" />
      </aside>

      <div v-if="mapStore.loading" class="absolute inset-0 z-30 flex items-center justify-center gap-3 bg-surface text-sm text-text-2">
        <Loader2 :size="18" class="animate-spin text-brand" />
        <span>Initializing map engine…</span>
      </div>

      <!-- Required OpenStreetMap attribution for the fetched OSM data. -->
      <div class="glass absolute bottom-3 left-1/2 z-[12] -translate-x-1/2 whitespace-nowrap rounded-full px-2.5 py-1 text-[11px] text-text-3">
        <a
          href="https://www.openstreetmap.org/copyright"
          target="_blank"
          rel="noopener noreferrer"
          class="text-inherit no-underline hover:text-brand hover:underline"
        >© OpenStreetMap contributors</a>
      </div>
    </main>

    <Toast />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import {
  Layers as LayersIcon,
  MessageSquare,
  Maximize2,
  ChevronLeft,
  ChevronRight,
  Settings2,
  ArrowRight,
  X,
  Loader2,
} from 'lucide-vue-next'
import { createHkLayer, createInitialLayers } from '@/layouts/layer'
import { HK_GREEN_LEGEND } from '@/lib/greenSpace'
import { HK_DISTRICTS_BBOX } from '@/lib/hkDistricts'
import { loadHkLayers } from '@/lib/hkLayers'
import { useMapStore } from '@/stores/mapStore'
import { useChatStore } from '@/stores/chatStore'
import { useWorkspaceStore } from '@/stores/workspaceStore'

import ThemeSwitch from '@/components/ThemeSwitch.vue'
import PropertyCard from '@/components/PropertyCard.vue'
import Layers from '@/components/layer/Layers.vue'
import MapComponent from '@/components/map.vue'
import AIChat from '@/components/chat/index.vue'
import Button from '@/components/ui/Button.vue'
import Tooltip from '@/components/ui/Tooltip.vue'
import Toast from '@/components/ui/Toast.vue'

const mapStore = useMapStore()
const chatStore = useChatStore()
const workspace = useWorkspaceStore()

const initialViewState = {
  longitude: 114.101275961,
  latitude: 22.50870175,
  zoom: 16,
}

// Seed the scene once. The store owns the registry; modules only provide
// factories, so there is no mutable singleton left to import.
let seeded = false
if (!seeded) {
  createInitialLayers().forEach((layer) => mapStore.layers.addLayer(layer))
  seeded = true
}

// The themed datasets are several MB of JSON each; load them as separate
// chunks so they never bloat the initial bundle. They register as hidden
// layers, ready to be toggled in the layer panel.
void loadHkLayers().then((configs) => {
  configs.forEach((cfg) => mapStore.layers.addLayer(createHkLayer(cfg)))
})

const selectedRegion = computed(() => mapStore.selectedRegion)
const selectedName = computed(() => {
  const props = selectedRegion.value?.properties
  return (props?.name as string) || (props?.id as string) || 'Selected feature'
})

const askAboutSelection = () => {
  if (!selectedRegion.value) return
  chatStore.draft = `分析当前选中的要素 ${selectedName.value}，并说明它的空间特征。`
  workspace.showPanel('chat', true)
}

const fitHongKong = () => {
  mapStore.fitBounds(HK_DISTRICTS_BBOX, { padding: 40, duration: 900 })
}

const districtsVisible = ref(true)
const toggleDistricts = () => {
  districtsVisible.value = !districtsVisible.value
  mapStore.setLayerVisibility('hk-districts-Layer', districtsVisible.value)
}

const handleMapClick = () => {
  // Clicking empty map space clears the selection; a feature click is handled
  // by the deck.gl layer's onClick in layer.ts.
  mapStore.updateHoveredRegion(null)
}

let mapLoadTimer: ReturnType<typeof setTimeout> | null = null
onMounted(() => {
  mapLoadTimer = setTimeout(() => {
    if (mapStore.loading) {
      console.warn('[GeoAI] map load timeout')
      mapStore.loading = false
    }
  }, 10000)
})
onUnmounted(() => {
  if (mapLoadTimer) clearTimeout(mapLoadTimer)
  mapStore.detach()
})

const handleFullScreen = () => {
  if (!document.fullscreenElement) document.documentElement.requestFullscreen()
  else document.exitFullscreen()
}
</script>
