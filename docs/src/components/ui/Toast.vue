<template>
  <div class="pointer-events-none fixed bottom-5 left-1/2 z-[100] flex -translate-x-1/2 flex-col items-center gap-2">
    <TransitionGroup
      enter-active-class="transition duration-200 ease-out"
      enter-from-class="translate-y-2 opacity-0"
      leave-active-class="transition duration-150 ease-in"
      leave-to-class="translate-y-2 opacity-0"
      move-class="transition duration-200"
    >
      <div
        v-for="item in toasts"
        :key="item.id"
        class="glass pointer-events-auto flex items-center gap-2 rounded-lg px-3.5 py-2 text-sm text-text"
        role="status"
      >
        <CircleCheck v-if="item.type === 'success'" :size="15" class="shrink-0 text-brand" />
        <CircleAlert v-else-if="item.type === 'error'" :size="15" class="shrink-0 text-danger" />
        <Info v-else :size="15" class="shrink-0 text-text-3" />
        <span>{{ item.message }}</span>
      </div>
    </TransitionGroup>
  </div>
</template>

<script setup lang="ts">
import { CircleCheck, CircleAlert, Info } from 'lucide-vue-next'
import { useToast } from './useToast'

const { toasts } = useToast()
</script>
