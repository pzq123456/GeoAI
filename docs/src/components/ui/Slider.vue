<template>
  <SliderRoot
    v-model="values"
    :min="min"
    :max="max"
    :step="step"
    :disabled="disabled"
    class="relative flex w-full touch-none select-none items-center py-1.5"
  >
    <SliderTrack class="relative h-1.5 w-full grow overflow-hidden rounded-full bg-surface-2">
      <SliderRange class="absolute h-full bg-brand" />
    </SliderTrack>
    <SliderThumb
      class="block h-3.5 w-3.5 rounded-full border-2 border-brand bg-surface-solid shadow-sm outline-none transition-colors focus-visible:ring-2 focus-visible:ring-brand/30 disabled:opacity-50"
    />
  </SliderRoot>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { SliderRoot, SliderRange, SliderThumb, SliderTrack } from 'reka-ui'

const model = defineModel<number>({ default: 0 })

withDefaults(
  defineProps<{
    min?: number
    max?: number
    step?: number
    disabled?: boolean
  }>(),
  { min: 0, max: 100, step: 1, disabled: false },
)

// Reka UI models a slider as an array of thumb values; this thin wrapper keeps a
// scalar v-model so call sites stay as simple as a native slider binding.
const values = computed<number[]>({
  get: () => [model.value],
  set: (next) => {
    if (next.length) model.value = next[0]!
  },
})
</script>
