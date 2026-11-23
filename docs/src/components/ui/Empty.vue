<template>
  <div class="flex flex-col items-center justify-center gap-2 px-4 py-8 text-center">
    <div class="flex h-11 w-11 items-center justify-center rounded-full border border-border bg-surface-2 text-text-3">
      <slot name="icon"><Inbox :size="18" :stroke-width="1.6" /></slot>
    </div>
    <p class="text-xs text-text-3">{{ description }}</p>
    <slot />
  </div>
</template>

<script setup lang="ts">
import { Inbox } from 'lucide-vue-next'

withDefaults(defineProps<{ description?: string }>(), {
  description: 'Nothing here yet',
})
</script>
