<!-- docs/src/components/layer/LayerCard.vue -->
<template>
  <div
    class="flex flex-col gap-2 rounded-lg border border-border border-l-[3px] bg-surface-2 p-3 transition-opacity"
    :class="layer.visible ? 'border-l-brand-2' : 'border-l-transparent opacity-60'"
  >
    <div class="flex cursor-pointer items-center gap-2" @click="toggleExpand">
      <GripVertical :size="14" class="drag-handle shrink-0 cursor-grab text-text-3" />

      <Tooltip content="Toggle visibility">
        <button
          type="button"
          class="shrink-0 text-text-2 transition-colors hover:text-brand"
          @click.stop="toggleVisibility"
        >
          <Eye v-if="layer.visible" :size="14" />
          <EyeOff v-else :size="14" />
        </button>
      </Tooltip>

      <span class="max-w-[120px] truncate text-[13px] font-semibold text-text">{{ layer.id }}</span>

      <div class="ml-auto flex items-center gap-1.5">
        <Tooltip content="Download GeoJSON">
          <button
            type="button"
            class="text-text-3 transition-colors hover:text-brand"
            @click.stop="handleDownload"
          >
            <Download :size="13" />
          </button>
        </Tooltip>

        <Tooltip content="Remove layer">
          <button
            type="button"
            class="text-text-3 transition-colors hover:text-danger"
            @click.stop="handleRemove"
          >
            <Trash2 :size="13" />
          </button>
        </Tooltip>

        <ChevronDown
          :size="14"
          class="shrink-0 text-text-3 transition-transform duration-200"
          :class="layer.isExpanded ? 'rotate-180' : ''"
        />
      </div>
    </div>

    <Transition
      enter-active-class="transition duration-150 ease-out"
      enter-from-class="opacity-0"
      leave-active-class="transition duration-150 ease-in"
      leave-to-class="opacity-0"
    >
      <div v-show="layer.isExpanded" class="flex flex-col gap-2">
        <span class="text-xs text-text-2">Opacity: {{ layer.opacity.toFixed(1) }}</span>
        <Slider v-model="layer.opacity" :min="0" :max="1" :step="0.1" :disabled="!layer.visible" />

        <div class="flex items-center justify-between text-xs">
          <span class="text-text-2">{{ layer.visible ? 'Visible' : 'Hidden' }}</span>
          <span class="text-[11px] text-text-3">眼睛图标可切换显隐</span>
        </div>

        <slot name="custom-controls"></slot>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { GripVertical, Eye, EyeOff, ChevronDown, Download, Trash2 } from 'lucide-vue-next'
import type { LayerItem } from '@/composables/useLayerGroup'

import Slider from '@/components/ui/Slider.vue'
import Tooltip from '@/components/ui/Tooltip.vue'

const props = defineProps<{ layer: LayerItem }>()

const emit = defineEmits<{
  'toggle-expand': [id: string]
  'toggle-visibility': [layer: LayerItem]
  'remove-layer': [id: string]
  'download-layer': [layer: LayerItem]
}>()

const toggleExpand = () => emit('toggle-expand', props.layer.id)
const toggleVisibility = () => emit('toggle-visibility', props.layer)

// 触发下载事件
const handleDownload = () => {
  emit('download-layer', props.layer)
}

// 触发移除事件
const handleRemove = () => {
  emit('remove-layer', props.layer.id)
}
</script>
