<template>
  <div class="parent-container">
    <search-component @select="handleLocationSelect" />
    <div class="selected-item" v-if="selectedLocation">
      <h3>Selected Location:</h3>
      <pre>{{ selectedLocation }}</pre>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import SearchComponent from './SearchComponent.vue'

const selectedLocation = ref(null)

const handleLocationSelect = (location) => {
  selectedLocation.value = location
  console.log('Selected Location:', location)
}
</script>

<style scoped>
.parent-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 2rem;
}

.selected-item {
  margin-top: 1.5rem;
  padding: 1rem;
  border-radius: 8px;
  border: 1px solid var(--el-border-color);
  background: var(--el-fill-color-light);
}

.selected-item h3 {
  margin: 0 0 0.75rem;
  font-size: 1rem;
  font-weight: 600;
}

.selected-item pre {
  margin: 0;
  padding: 0.75rem;
  border-radius: 6px;
  background: var(--el-fill-color);
  font-size: 0.875rem;
  line-height: 1.5;
  white-space: pre-wrap;
  overflow-x: auto;
}
</style>