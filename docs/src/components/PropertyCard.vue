<template>
  <div class="property-container">
    <el-scrollbar v-if="hasData" max-height="300px">
      <el-descriptions
        class="custom-descriptions"
        :column="1"
        size="small"
        border
      >
        <el-descriptions-item 
          v-for="(value, key) in displayProps" 
          :key="key"
        >
          <template #label>
            <div class="prop-label">
              <el-icon><InfoFilled /></el-icon>
              {{ key }}
            </div>
          </template>

          <div class="prop-value-wrapper">
            <span class="prop-text">{{ value }}</span>
            <el-tooltip content="Copy Value" placement="top" :enterable="false">
              <el-button 
                link 
                type="primary" 
                class="copy-btn"
                @click="copyToClipboard(value)"
              >
                <el-icon><CopyDocument /></el-icon>
              </el-button>
            </el-tooltip>
          </div>
        </el-descriptions-item>
      </el-descriptions>
    </el-scrollbar>

    <el-empty 
      v-else 
      :image-size="60" 
      description="No Object Selected" 
    />
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { ElMessage } from 'element-plus';
import { InfoFilled, CopyDocument } from '@element-plus/icons-vue';

const props = defineProps(['data']);

const hasData = computed(() => props.data && Object.keys(displayProps.value).length > 0);

const displayProps = computed(() => {
  if (!props.data) return {};
  const source = props.data.properties || props.data;
  // 过滤掉复杂对象，只保留基础类型，并排除常用的冗余字段（如 ID）
  return Object.fromEntries(
    Object.entries(source).filter(([_, v]) => typeof v !== 'object' && v !== null)
  );
});

// 复制功能
const copyToClipboard = async (text) => {
  try {
    await navigator.clipboard.writeText(String(text));
    ElMessage({
      message: 'Copied to clipboard',
      type: 'success',
      duration: 1500,
      grouping: true // 避免多次点击弹出多个提示
    });
  } catch (err) {
    ElMessage.error('Copy failed');
  }
};
</script>

<style scoped>
.property-container {
  padding: 8px;
  background-color: var(--el-bg-color);
  border-radius: 8px;
}

/* 标签样式微调 */
.prop-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  color: var(--el-text-color-secondary);
  white-space: nowrap;
}

/* 值区域容器 */
.prop-value-wrapper {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.prop-text {
  font-family: 'Fira Code', monospace; /* 代码字体更有科技感 */
  font-size: 13px;
  word-break: break-all; /* 防止长字符串撑开表格 */
  color: var(--el-text-color-primary);
}

.copy-btn {
  padding: 4px;
  opacity: 0.3;
  transition: opacity 0.2s;
}

/* 只有鼠标滑过行时才显示复制按钮，保持界面清爽 */
.prop-value-wrapper:hover .copy-btn {
  opacity: 1;
}

/* 深度适配深色模式的边框颜色 */
:deep(.el-descriptions__border) {
  border-color: var(--el-border-color-lighter);
}
:deep(.el-descriptions__label.is-bordered-label) {
  background-color: var(--el-fill-color-light);
  width: 100px; /* 固定 Key 的宽度 */
}
</style>