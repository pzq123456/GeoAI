<template>
  <input
    v-model="model"
    :type="type"
    :placeholder="placeholder"
    :disabled="disabled"
    class="h-9 w-full rounded-lg border border-border bg-surface-solid px-3 text-sm text-text shadow-sm outline-none transition-colors placeholder:text-text-3 focus:border-brand focus:ring-2 focus:ring-brand/20 disabled:cursor-not-allowed disabled:opacity-50"
  />
</template>

<script setup lang="ts">
const model = defineModel<string>()

withDefaults(
  defineProps<{
    type?: string
    placeholder?: string
    disabled?: boolean
  }>(),
  { type: 'text', disabled: false },
)
</script>
