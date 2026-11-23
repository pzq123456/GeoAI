<template>
  <component
    :is="as"
    :type="as === 'button' ? type : undefined"
    :disabled="disabled || undefined"
    :class="classes"
  >
    <slot />
  </component>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { cva } from 'class-variance-authority'
import { cn } from './utils'

const buttonVariants = cva(
  'inline-flex shrink-0 items-center justify-center gap-1.5 whitespace-nowrap rounded-lg font-medium transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/40 disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        default: 'bg-brand text-white shadow-sm hover:bg-brand/90',
        ghost: 'text-text-2 hover:bg-surface-2 hover:text-text',
        link: 'text-brand underline-offset-4 hover:underline',
        destructive: 'bg-danger text-white shadow-sm hover:bg-danger/90',
        outline: 'border border-border bg-transparent text-text hover:bg-surface-2',
      },
      size: {
        sm: 'h-7 rounded-md px-2.5 text-xs',
        md: 'h-9 px-3.5 text-sm',
        icon: 'h-8 w-8 rounded-md',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'md',
    },
  },
)

type Props = {
  variant?: 'default' | 'ghost' | 'link' | 'destructive' | 'outline'
  size?: 'sm' | 'md' | 'icon'
  as?: string
  type?: 'button' | 'submit' | 'reset'
  disabled?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'default',
  size: 'md',
  as: 'button',
  type: 'button',
  disabled: false,
})

const classes = computed(() => cn(buttonVariants({ variant: props.variant, size: props.size })))
</script>
