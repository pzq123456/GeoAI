<template>
  <div class="property-card">
    <div v-if="data">
      <div v-for="(value, key) in displayProps" :key="key" class="prop-item">
        <span class="label">{{ key }}:</span>
        <span class="value">{{ value }}</span>
      </div>
    </div>
    <div v-else class="empty">No Data Selected</div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
const props = defineProps(['data']);

const displayProps = computed(() => {
  if (!props.data) return {};
  // 兼容 GeoJSON 格式或普通对象
  const source = props.data.properties || props.data;
  // 过滤掉 object 类型的复杂字段，只留字符串和数字
  return Object.fromEntries(
    Object.entries(source).filter(([_, v]) => typeof v !== 'object')
  );
});
</script>

<style scoped>
.property-card {
  padding: 10px;
  font-family: monospace;
  font-size: 12px;
  line-height: 1.6;
}
.prop-item { display: flex; gap: 8px; border-bottom: 1px solid #eee; }
.label { color: #888; font-weight: bold; }
.empty { color: #999; font-style: italic; }
</style>