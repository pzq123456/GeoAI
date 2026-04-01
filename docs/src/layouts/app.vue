<template>
  <div class="layout-fixed-height" v-loading="mapLoading" element-loading-text="Initializing Map System...">
    <el-splitter style="height: 100vh">

      <el-splitter-panel :size="300" :min="250" collapsible>
        <div class="panel-inner">
          <SidebarControls @toggle-fullscreen="handleFullScreen" @toggle-theme="toggleTheme" />
          <div class="sidebar-content">
            <Layers :layerGroup="layerGroup" :onUpdated="updateDeckLayers" />

            <el-divider />

            <PropertyCard :data="selectedRegion" />
          </div>
        </div>
      </el-splitter-panel>

      <el-splitter-panel>
        <div class="panel-inner">
          <MapComponent v-if="initialViewState" :center="[initialViewState.longitude, initialViewState.latitude]"
            :zoom="initialViewState.zoom" ref="map" @map-loaded="handleMapLoaded" />
        </div>
      </el-splitter-panel>

      <el-splitter-panel :size="350" :min="300" collapsible>
        <div class="panel-inner relative-container">
          <div class="ai-component-wrapper">
            <AIChat @refresh-map="updateDeckLayers" />
          </div>
        </div>
      </el-splitter-panel>

    </el-splitter>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import { layerGroup } from '@/layouts/layer.js';
import { useDeckOverlay } from '@/composables/useDeckOverlay.js';
import { useMapStore } from '@/stores/mapStore';

import SidebarControls from '@/components/SidebarControls.vue';
import Layers from '@/components/layer/Layers.vue';
import MapComponent from '@/components/map.vue';
import AIChat from '@/components/chat/index.vue';

const mapLoading = ref(true);
const mapStore = useMapStore();
let deckMap = null;

const initialViewState = {
  longitude: 114.1564928,
  latitude: 22.2780393,
  zoom: 16,
};

// 1. 接回：图层更新逻辑
const updateDeckLayers = () => {
  if (deckMap) {
    deckMap.setProps({
      layers: layerGroup.getLayers(),
    });
  }
};

// 2. 接回：地图拾取与高亮的核心逻辑
const selectedRegion = computed(() => mapStore.selectedRegion);

watch(selectedRegion, (newRegion) => {
  // 查找并更新高亮图层数据
  const highlightLayer = layerGroup.layers.find((l) => l.id === 'Highlight-Layer');
  if (highlightLayer) {
    highlightLayer.data = newRegion ? [newRegion] : [];
    updateDeckLayers();
  }
});

const handleMapLoaded = (mapInstance) => {
  deckMap = useDeckOverlay(mapInstance);
  updateDeckLayers();
  mapLoading.value = false;
};

const handleFullScreen = () => {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen();
  } else {
    if (document.exitFullscreen) document.exitFullscreen();
  }
};

const toggleTheme = () => {
  console.log('Theme toggle logic here');
};
</script>

<style scoped>
.layout-fixed-height {
  height: 100vh;
  width: 100vw;
  overflow: hidden;
  background-color: var(--el-bg-color);
}

.panel-inner {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.relative-container {
  position: relative;
  /* 核心：为内部绝对定位的 AIChat 提供基准 */
}

.ai-component-wrapper {
  flex: 1;
  position: relative;
  overflow: hidden;
}

.sidebar-content {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid var(--el-border-color-light);
  background-color: var(--el-bg-color-overlay);
}

.panel-title {
  font-weight: 600;
  color: var(--el-text-color-primary);
}

:deep(.mapboxgl-map) {
  width: 100% !important;
  height: 100% !important;
}
</style>