<template>
  <div class="flex flex-col gap-2">
    <!-- Summary bar -->
    <div class="flex items-center gap-2 rounded-lg border border-border bg-surface-2 px-2.5 py-1.5 text-[11px]">
      <span class="font-semibold text-text-2">执行链路</span>
      <span class="rounded-full bg-surface-solid px-1.5 py-0.5 font-mono text-text-3">{{ toolSteps.length }} 工具</span>
      <span v-if="totalLatency" class="rounded-full bg-surface-solid px-1.5 py-0.5 font-mono text-text-3">
        总耗时 {{ totalLatency }}ms
      </span>
      <span v-if="failedCount" class="rounded-full border border-danger/30 px-1.5 py-0.5 text-danger">
        {{ failedCount }} 失败
      </span>
      <span v-if="isRunning" class="ml-auto flex items-center gap-1 text-brand">
        <Loader2 :size="12" class="animate-spin" /> 运行中
      </span>
      <span v-else-if="steps.length" class="ml-auto flex items-center gap-1 text-brand">
        <CircleCheck :size="12" /> 完成
      </span>
    </div>

    <!-- Timeline -->
    <div v-if="steps.length" class="relative flex flex-col">
      <div
        v-for="(step, index) in steps"
        :key="step.id"
        class="group relative flex gap-2.5 pb-2.5 last:pb-0"
      >
        <!-- vertical connector -->
        <div
          v-if="index < steps.length - 1"
          class="absolute left-[9px] top-5 h-[calc(100%-12px)] w-px bg-border"
        ></div>

        <!-- status node -->
        <div class="relative z-[1] mt-0.5 shrink-0">
          <div
            class="grid h-[19px] w-[19px] place-items-center rounded-full border"
            :class="nodeClass(step)"
          >
            <Loader2 v-if="isStepRunning(step)" :size="11" class="animate-spin" />
            <CircleCheck v-else-if="step.status === 'success'" :size="11" />
            <CircleX v-else-if="step.status === 'error'" :size="11" />
            <Circle v-else :size="11" />
          </div>
        </div>

        <!-- content -->
        <div class="min-w-0 flex-1">
          <button
            type="button"
            class="flex w-full items-start gap-1.5 rounded-md px-1 py-0.5 text-left transition-colors hover:bg-surface-2"
            :disabled="!step.detail"
            @click="toggle(step.id)"
          >
            <span class="min-w-0 flex-1 truncate text-[12px]" :class="step.status === 'error' ? 'text-danger' : 'text-text'">
              {{ step.title }}
            </span>
            <span v-if="step.latencyMs !== undefined" class="shrink-0 font-mono text-[11px] text-text-3">
              {{ step.latencyMs }}ms
            </span>
            <component
              :is="step.detail ? (expanded[step.id] ? ChevronDown : ChevronRight) : Minus"
              :size="12"
              class="mt-0.5 shrink-0 text-text-3"
            />
          </button>

          <!-- expanded detail -->
          <div v-if="expanded[step.id] && step.detail" class="mt-1 overflow-hidden rounded-md border border-border bg-surface-solid">
            <pre class="max-h-40 overflow-auto whitespace-pre-wrap break-all p-2 font-mono text-[11px] leading-relaxed text-text-2">{{ pretty(step.detail) }}</pre>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="rounded-lg border border-dashed border-border px-3 py-4 text-center text-[11px] text-text-3">
      暂无执行步骤
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive } from 'vue'
import {
  ChevronDown, ChevronRight, Circle, CircleCheck, CircleX, Loader2, Minus,
} from 'lucide-vue-next'
import type { TraceEntry } from '@/types'

const props = defineProps<{
  steps: TraceEntry[]
  isRunning: boolean
}>()

const expanded = reactive<Record<string, boolean>>({})

const toolSteps = computed(() => props.steps.filter((s) => s.kind === 'tool_call'))
const totalLatency = computed(() => {
  const ms = props.steps.reduce((sum, s) => sum + (s.latencyMs ?? 0), 0)
  return ms > 0 ? ms : 0
})
const failedCount = computed(() => props.steps.filter((s) => s.status === 'error').length)

const isStepRunning = (step: TraceEntry) =>
  props.isRunning && step.status !== 'success' && step.status !== 'error'

const nodeClass = (step: TraceEntry) => {
  if (isStepRunning(step)) return 'border-brand/40 bg-brand-soft text-brand'
  if (step.status === 'success') return 'border-brand/40 bg-brand-soft text-brand'
  if (step.status === 'error') return 'border-danger/40 bg-danger/10 text-danger'
  return 'border-border bg-surface-2 text-text-3'
}

const toggle = (id: string) => {
  expanded[id] = !expanded[id]
}

const pretty = (raw: string): string => {
  try {
    return JSON.stringify(JSON.parse(raw), null, 2)
  } catch {
    return raw
  }
}
</script>
