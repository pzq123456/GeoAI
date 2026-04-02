<template>
  <div class="theme-switch-wrapper">
    <el-switch
      v-model="isDark"
      inline-prompt
      :active-action-icon="Moon"
      :inactive-action-icon="Sunny"
      class="custom-theme-switch"
    />
  </div>
</template>

<script setup>
import { useData } from 'vitepress'
import { Sunny, Moon } from '@element-plus/icons-vue'

const { isDark } = useData()
</script>

<style scoped>
.theme-switch-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
}

.custom-theme-switch {
  /* 基础轨道高度微调，让它更精致 */
  height: 24px;
  
  /* --- 浅色模式样式 (Inactive) --- */
  --el-switch-off-color: #f0f2f5;
  /* 图标本身颜色 (橙色太阳) */
  --el-switch-on-color: #2c2c2c;
}

/* 关键：深度定制内部圆形按钮 (Action) 和 图标 (Icon) */

/* 1. 调整圆形滑块的背景 */
:deep(.el-switch__action) {
  background-color: transparent !important; /* 移除默认白底 */
  box-shadow: none !important;
}

/* 2. 浅色模式下的太阳图标：深灰色轨道 + 橙色太阳 */
:deep(.el-switch__core) {
  border: 1px solid var(--el-border-color-lighter) !important;
}

:deep(.el-switch:not(.is-checked) .el-icon) {
  color: #ff9e2c !important; /* 太阳暖橙色 */
  filter: drop-shadow(0 0 2px rgba(255, 158, 44, 0.4));
}

/* 3. 深色模式下的月亮图标：深黑色轨道 + 金色月亮 */
:deep(.el-switch.is-checked .el-switch__core) {
  background-color: #1a1a1a !important;
  border-color: #333 !important;
}

:deep(.el-switch.is-checked .el-icon) {
  color: #f1c40f !important; /* 月亮亮金色 */
  filter: drop-shadow(0 0 3px rgba(241, 196, 15, 0.4));
}

/* 4. 解决图标太小看不清的问题 */
:deep(.el-switch__action .el-icon) {
  font-size: 14px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

/* 鼠标悬停时的微交互 */
.custom-theme-switch:hover :deep(.el-switch__core) {
  border-color: var(--el-color-primary-light-5) !important;
}
</style>