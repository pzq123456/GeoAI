<template>
  <div class="layout-fixed-height" v-loading="mapLoading" element-loading-text="Initializing Map System...">
    <el-splitter class="main-splitter">

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
          <MapComponent 
            v-if="initialViewState" 
            :center="[initialViewState.longitude, initialViewState.latitude]"
            :zoom="initialViewState.zoom" 
            ref="map" 
            @map-loaded="handleMapLoaded" 
          />
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
  longitude: 114.101275961,
  latitude: 22.50870175,
  zoom: 16,
};

const updateDeckLayers = () => {
  if (deckMap) {
    deckMap.setProps({
      layers: layerGroup.getLayers(),
    });
  }
};

const selectedRegion = computed(() => mapStore.selectedRegion);

watch(selectedRegion, (newRegion) => {
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
/* 修复点：强制 html/body 溢出隐藏，这是最外层的保险 */
:global(html, body) {
  margin: 0;
  padding: 0;
  overflow: hidden;
  width: 100%;
  height: 100%;
}

.layout-fixed-height {
  height: 100vh;
  width: 100%; /* 修复：必须是 100% 而不是 100vw */
  overflow: hidden; 
  background-color: var(--el-bg-color);
  display: flex;
}

.main-splitter {
  height: 100% !important; /* 修复：继承父级高度 */
  width: 100% !important;
  border: none !important; /* 修复：移除可能导致 1px 溢出的边框 */
}

/* 修复点：面板容器必须锁定 overflow，防止内部微小溢出 */
.panel-inner {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  overflow: hidden; 
}

.relative-container {
  position: relative;
}

.ai-component-wrapper {
  flex: 1;
  position: relative;
  overflow: hidden;
}

.sidebar-content {
  flex: 1;
  overflow-y: auto; /* 仅在侧边栏内容区允许垂直滚动 */
  overflow-x: hidden; /* 严禁侧边栏出现横向滚动 */
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

/* 修复点：移除 Element Splitter 默认边框影响 */
:deep(.el-splitter__panel) {
  overflow: hidden;
}
</style>