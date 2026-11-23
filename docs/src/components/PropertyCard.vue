<template>
  <div class="p-0.5">
    <dl
      v-if="hasData"
      class="max-h-[300px] divide-y divide-border overflow-y-auto rounded-lg border border-border bg-surface-solid text-sm"
    >
      <div
        v-for="(value, key) in displayProps"
        :key="key"
        class="flex items-start justify-between gap-3 px-3 py-2"
      >
        <dt class="shrink-0 text-xs font-medium text-text-2">{{ key }}</dt>
        <dd class="flex min-w-0 items-center justify-end gap-1.5">
          <span class="break-all text-right text-xs text-text">{{ value }}</span>
          <Tooltip content="Copy value">
            <Button
              variant="ghost"
              size="icon"
              class="h-6 w-6 shrink-0 opacity-40 transition-opacity hover:opacity-100"
              @click="copyToClipboard(value)"
            >
              <Copy :size="12" />
            </Button>
          </Tooltip>
        </dd>
      </div>
    </dl>

    <Empty v-else description="No object selected" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Copy } from 'lucide-vue-next'
import type { GeoJsonFeature } from '@/types'

import Button from '@/components/ui/Button.vue'
import Tooltip from '@/components/ui/Tooltip.vue'
import Empty from '@/components/ui/Empty.vue'
import { toast } from '@/components/ui/useToast'

const props = defineProps<{ data?: GeoJsonFeature | null }>()

const hasData = computed(() => props.data && Object.keys(displayProps.value).length > 0)

const displayProps = computed(() => {
  if (!props.data) return {}
  const source = props.data.properties || props.data
  // 过滤掉复杂对象，只保留基础类型，并排除常用的冗余字段（如 ID）
  return Object.fromEntries(
    Object.entries(source).filter(([_, v]) => typeof v !== 'object' && v !== null)
  )
})

// 复制功能
const copyToClipboard = async (text: unknown) => {
  try {
    await navigator.clipboard.writeText(String(text))
    toast.success('Copied to clipboard', { duration: 1500 })
  } catch {
    toast.error('Copy failed')
  }
}
</script>
