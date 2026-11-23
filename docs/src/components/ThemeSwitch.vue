<template>
  <button
    type="button"
    class="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-border bg-surface-2 text-text-2 transition-colors hover:border-brand hover:text-brand"
    :aria-label="isDark ? 'Switch to light theme' : 'Switch to dark theme'"
    :title="isDark ? 'Light mode' : 'Dark mode'"
    @click="isDark = !isDark"
  >
    <Sun v-if="isDark" :size="15" class="text-accent" />
    <Moon v-else :size="15" class="text-brand" />
  </button>
</template>

<script setup lang="ts">
import { Sun, Moon } from 'lucide-vue-next'
import { useTheme } from '@/composables/useTheme'

const { isDark } = useTheme()
</script>
