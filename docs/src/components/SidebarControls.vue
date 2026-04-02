<template>
  <div class="sidebar-toolbar">
    <div class="tool-group">
      <el-button-group>
        <el-tooltip content="Toggle Fullscreen" placement="bottom">
          <el-button :icon="FullScreen" @click="$emit('toggle-fullscreen')" />
        </el-tooltip>
        <el-tooltip content="Refresh Layers" placement="bottom">
          <el-button :icon="Refresh" @click="handleRefresh" />
        </el-tooltip>
        
      </el-button-group>
    </div>
    
    <div class="tool-group">
       <el-button :icon="Setting" plain circle />
    </div>
  </div>
</template>

<script setup>
import { FullScreen, Refresh, Setting } from '@element-plus/icons-vue';

defineEmits(['toggle-fullscreen'])

const handleRefresh = () => {
  window.location.reload() // 或者执行你的刷新逻辑
}
</script>

<style scoped>
.sidebar-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background-color: var(--el-bg-color-overlay);
  border-bottom: 1px solid var(--el-border-color-light);
}

/* 移除硬编码的颜色，使用 CSS 变量确保深色模式兼容 */
:deep(.el-button) {
  border: none;
  background: transparent;
  color: var(--el-text-color-regular);
}

:deep(.el-button:hover) {
  background: var(--el-fill-color-light);
  color: var(--el-color-primary);
}
</style>