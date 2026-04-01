<template>
  <div class="search-container">
    <div class="search-wrapper">
      <el-autocomplete
        v-model="searchQuery"
        :fetch-suggestions="querySearchAsync"
        placeholder="Search for a state or county..."
        @select="handleSelect"
        clearable
        class="search-input"
        :loading="loading"
      >
        <template #suffix>
          <el-icon>
            <search />
          </el-icon>
        </template>
        <template #default="{ item }">
          <div class="suggestion-item">
            <span class="state" v-if="item.type === 'state'">{{ item.value }}</span>
            <span class="county" v-else>{{ item.value }}, {{ item.state }}</span>
          </div>
        </template>
      </el-autocomplete>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { data } from '@/loaders/usa2014_2024.data.js'

const emit = defineEmits(['select'])

const searchQuery = ref('')
const loading = ref(false)

// 缓存 suggestions
let suggestions = []
const seen = new Set()

data.features.forEach(feature => {
  const { NAME_1_x: state, NAME_2_x: county } = feature.properties

  const stateKey = `state-${state}`
  if (!seen.has(stateKey)) {
    seen.add(stateKey)
    suggestions.push({
      value: state,
      type: 'state',
      raw: feature,
      state: state
    })
  }

  if (county) {
    const countyKey = `county-${state}-${county}`
    if (!seen.has(countyKey)) {
      seen.add(countyKey)
      suggestions.push({
        value: county,
        type: 'county',
        raw: feature,
        state: state
      })
    }
  }
})

const querySearchAsync = async (queryString, cb) => {
  loading.value = true
  if (!queryString) {
    cb([])
    loading.value = false
    return
  }

  const queryLower = queryString.toLowerCase()
  const queryParts = queryLower.split(/[, ]+/).filter(part => part)

  const filtered = suggestions
    .map(item => {
      let score = 0
      const valueLower = item.value.toLowerCase()
      const stateLower = item.state.toLowerCase()

      if (queryParts.length > 1) {
        // 多词查询，匹配州和县组合
        const countyMatch = item.type === 'county' && valueLower.includes(queryParts[0])
        const stateMatch = stateLower.includes(queryParts[1])
        if (countyMatch && stateMatch) {
          score = 4
        }
      } else {
        // 单词查询
        if (item.type === 'county' && valueLower.includes(queryLower) && stateLower.includes(queryLower)) {
          score = 3
        } else if (item.type === 'county' && valueLower.includes(queryLower)) {
          score = 2
        } else if (item.type === 'state' && valueLower.includes(queryLower)) {
          score = 1
        }
      }

      return { ...item, score }
    })
    .filter(item => item.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, 10)

  cb(filtered)
  loading.value = false
}

const handleSelect = (item) => {
  emit('select', item.raw)
}
</script>

<style scoped>
.search-container {
  max-width: 100%;
}

.search-wrapper {
  position: relative;
}

.search-input :deep(.el-input__wrapper) {
  border-radius: 8px;
  box-shadow: 0 0 0 1px var(--el-border-color);
  padding: 0 12px;
  transition: box-shadow 0.2s;
}

.search-input :deep(.el-input__wrapper:hover),
.search-input :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px var(--el-color-primary);
}

.search-input :deep(.el-autocomplete__loading-indicator) {
  right: 2.5rem;
  color: var(--el-color-primary);
}

.suggestion-item {
  padding: 8px 12px;
}

.suggestion-item .state {
  font-weight: 600;
}

.suggestion-item .county::before {
  content: "•";
  margin: 0 6px;
  color: var(--el-border-color);
}
</style>