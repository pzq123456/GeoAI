<!-- docs/src/components/layer/Layers.vue -->
<template>
  <div class="container">
    <LayerHeader 
      :layers="layerGroup.layers" 
      :is-layer-list-visible="isLayerListVisible"
      @toggle-all-details="toggleAllDetails" 
      @toggle-layer-list="toggleLayerList" 
    />

    <div class="layer-container" ref="el" v-show="isLayerListVisible">
      <component 
        :is="getCardVomponents(layer.id)"
        v-for="layer in layerGroup.layers"
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

<script setup>
import { ref, watch } from 'vue';
import { useDraggable } from 'vue-draggable-plus';
import { LayerGroup } from '@/composables/useLayerGroup';
import pkg from 'lodash';
const { throttle } = pkg;

import LayerHeader from './LayerHeader.vue';
import BasicLayerCard from './LayerCard.vue';

const props = defineProps({
  layerGroup: {
    type: LayerGroup,
    required: true,
  },
  onUpdated: {
    type: Function,
    default: () => { },
  },
});

// 不要解构 props，直接引用
const isLayerListVisible = ref(true); // 默认建议设为 true，方便调试

const throttledUpdate = throttle(() => {
  props.onUpdated();
}, 200);

// 监听内部状态变化
watch(
  () => props.layerGroup.layers.map(layer => layer.state),
  () => throttledUpdate(),
  { deep: true }
);

const toggleExpand = (id) => {
  const layer = props.layerGroup.layers.find(item => item.id === id);
  if (layer) layer.isExpanded = !layer.isExpanded;
};

const toggleVisibility = (layer) => {
  layer.visible = !layer.visible;
};

// --- 新增：处理删除 ---
const handleRemoveLayer = (id) => {
  props.layerGroup.removeLayer(id);
  props.onUpdated();
};

// --- 新增：处理下载 ---
const handleDownloadLayer = (layer) => {
  const data = layer.data?.features || layer.data;
  if (!data) return;
  const blob = new Blob([JSON.stringify(data)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${layer.id}.geojson`;
  a.click();
  URL.revokeObjectURL(url);
};

const toggleLayerList = () => {
  isLayerListVisible.value = !isLayerListVisible.value;
};

const toggleAllDetails = () => {
  const allExpanded = props.layerGroup.layers.every(layer => layer.isExpanded);
  props.layerGroup.layers.forEach(layer => {
    layer.isExpanded = !allExpanded;
  });
};

const el = ref();
useDraggable(el, props.layerGroup.layers, {
  animation: 150,
  handle: '.drag-handle', // 记得在 LayerCard 里给图标加上这个 class
  onUpdate() {
    props.onUpdated();
  }
});

function getCardVomponents() {
  return BasicLayerCard;
}
</script>

<style scoped>
.container {
  margin: 1px;
  display: flex;
  flex-direction: column;
  width: 99%;
  border-radius: 8px;
  transition: background-color 0.3s ease, border-radius 0.3s ease;
  border: 1px solid var(--vp-c-border);
  overflow-y: auto;
  overflow: hidden;
}

.layer-container {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.5rem;
  width: 100%;
  height: auto;
  margin: auto;
  background-color: var(--vp-c-bg);
  border-radius: 0 0 8px 8px;
}

.ghost {
  opacity: 0.2;
}
</style>