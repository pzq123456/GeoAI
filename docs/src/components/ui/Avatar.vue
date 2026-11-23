<template>
  <AvatarRoot
    :class="cn(
      'relative inline-flex shrink-0 items-center justify-center overflow-hidden rounded-full border border-border bg-brand-soft text-brand',
      size === 'sm' ? 'h-[26px] w-[26px]' : 'h-8 w-8',
    )"
  >
    <AvatarImage v-if="src" :src="src" :alt="alt" class="h-full w-full object-cover" />
    <AvatarFallback class="flex h-full w-full items-center justify-center">
      <slot>
        <User :size="size === 'sm' ? 14 : 16" :stroke-width="1.8" />
      </slot>
    </AvatarFallback>
  </AvatarRoot>
</template>

<script setup lang="ts">
import { AvatarRoot, AvatarImage, AvatarFallback } from 'reka-ui'
import { User } from 'lucide-vue-next'
import { cn } from './utils'

withDefaults(
  defineProps<{
    src?: string
    alt?: string
    size?: 'sm' | 'md'
  }>(),
  { src: '', alt: '', size: 'md' },
)
</script>
