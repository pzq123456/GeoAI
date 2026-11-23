<template>
  <textarea
    ref="inner"
    v-model="model"
    :rows="rows"
    :placeholder="placeholder"
    :disabled="disabled"
    class="w-full resize-none rounded-lg border border-transparent bg-transparent px-1 py-0.5 text-sm leading-relaxed text-text outline-none placeholder:text-text-3 focus:border-transparent focus:ring-0 disabled:cursor-not-allowed disabled:opacity-50"
  />
</template>

<script setup lang="ts">
import { ref } from 'vue'

const model = defineModel<string>()

withDefaults(
  defineProps<{
    rows?: number
    placeholder?: string
    disabled?: boolean
  }>(),
  { rows: 2, disabled: false },
)

const inner = ref<HTMLTextAreaElement | null>(null)
defineExpose({ focus: () => inner.value?.focus() })
</script>
