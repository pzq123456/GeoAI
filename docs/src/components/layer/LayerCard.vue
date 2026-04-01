<!-- docs/src/components/layer/LayerCard.vue -->
<template>
  <div class="layer-item" :class="{ 'hidden-layer': !layer.visible, 'active': layer.visible }">
    <div class="layer-header" @click="toggleExpand">
      <el-icon class="drag-handle"><Rank /></el-icon>
      
      <el-icon @click.stop="toggleVisibility">
        <component :is="layer.visible ? 'View' : 'Hide'" />
      </el-icon>

      <span class="layer-id">{{ layer.id }}</span>

      <div class="leftBtn">
        <el-tooltip content="Download GeoJSON" placement="top">
          <el-icon class="action-icon" @click.stop="handleDownload">
            <Download />
          </el-icon>
        </el-tooltip>

        <el-tooltip content="Remove Layer" placement="top">
          <el-icon class="action-icon delete-icon" @click.stop="handleRemove">
            <Delete />
          </el-icon>
        </el-tooltip>

        <el-icon :class="{ 'expanded': layer.isExpanded }">
          <ArrowDownBold />
        </el-icon>
      </div>
    </div>

    <Transition name="fade">
      <div v-show="layer.isExpanded" class="layer-details">
        <span class="layer-opacity">Opacity: {{ layer.opacity.toFixed(1) }}</span>
        <el-slider v-model="layer.opacity" :min="0" :max="1" :step="0.1" :show-tooltip="false" :disabled="!layer.visible" />
        
        <div class="status-row">
          <span class="layer-visibility">{{ layer.visible ? 'Visible' : 'Hidden' }}</span>
          <el-checkbox v-model="layer.visible" />
        </div>
            
        <slot name="custom-controls"></slot>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { defineProps, defineEmits } from 'vue';
import { Rank, View, Hide, ArrowDownBold, Download, Delete } from '@element-plus/icons-vue';

const props = defineProps({
  layer: { type: Object, required: true }
});

const emit = defineEmits(['toggle-expand', 'toggle-visibility', 'remove-layer', 'download-layer']);

const toggleExpand = () => emit('toggle-expand', props.layer.id);
const toggleVisibility = () => emit('toggle-visibility', props.layer);

// 触发下载事件
const handleDownload = () => {
  emit('download-layer', props.layer);
};

// 触发移除事件
const handleRemove = () => {
  emit('remove-layer', props.layer.id);
};
</script>

<style scoped>
.layer-item {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.75rem;
  background-color: var(--vp-c-bg-soft);
  border-radius: 4px;
  cursor: move;
  border: 1px solid var(--vp-c-default-3);
  transition: background-color 0.3s ease, border-radius 0.3s ease;
}

.layer-item.active {
  border-left: 3px solid var(--vp-c-brand-2);
}

.layer-item.hidden-layer {
  opacity: 0.6;
  background-color: var(--vp-c-default-soft);
}

.layer-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
}

.layer-details {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.layer-opacity,
.layer-visibility {
  color: var(--vp-c-text-2);
}

.leftBtn {
  display: flex;
  justify-content: center;
  align-items: center;
  margin-left: auto;
}

/* 箭头旋转样式 */
.leftBtn .el-icon {
  transition: transform 0.3s ease;
}

.leftBtn .el-icon.expanded {
  transform: rotate(180deg);
}

/* 图标交互样式 */
.action-icon {
  margin-right: 8px;
  cursor: pointer;
  transition: color 0.2s;
  font-size: 14px;
}

.action-icon:hover {
  color: var(--vp-c-brand-1);
}

.delete-icon:hover {
  color: var(--el-color-danger);
}

.status-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.drag-handle {
  cursor: grab;
  color: var(--vp-c-text-3);
}

.layer-id {
  font-weight: bold;
  color: var(--vp-c-text-1);
  font-size: 13px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 120px;
}
</style>