<!-- docs/src/components/layer/LayerHeader.vue -->
<template>
  <div class="flex items-center justify-between rounded-t-lg bg-bg px-3 py-2.5">
    <Tooltip content="Expand all layers">
      <Button variant="ghost" size="icon" class="h-6 w-6" @click="toggleAllDetails">
        <Minus v-if="allExpanded" :size="14" />
        <Plus v-else :size="14" />
      </Button>
    </Tooltip>

    <span class="text-sm text-text-3">Layer Control</span>

    <Tooltip content="Toggle layer list">
      <Button
        variant="ghost"
        size="icon"
        class="h-6 w-6 transition-transform"
        :class="!isLayerListVisible ? 'rotate-180' : ''"
        @click="toggleLayerList"
      >
        <ArrowUp :size="14" />
      </Button>
    </Tooltip>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ArrowUp, Minus, Plus } from 'lucide-vue-next'
import type { LayerItem } from '@/composables/useLayerGroup'

import Button from '@/components/ui/Button.vue'
import Tooltip from '@/components/ui/Tooltip.vue'

const props = defineProps<{
  layers: LayerItem[]
  isLayerListVisible: boolean
}>()

const emit = defineEmits<{
  'toggle-all-details': []
  'toggle-layer-list': []
}>()

const allExpanded = computed(() => props.layers.every(layer => layer.isExpanded))

const toggleAllDetails = () => {
  emit('toggle-all-details')
}

const toggleLayerList = () => {
  emit('toggle-layer-list')
}
</script>
