<template>
  <div class="flex h-full min-h-0 flex-col">
    <div class="flex shrink-0 items-center gap-2 px-3 pb-2 pt-3">
      <div class="flex items-center gap-2">
        <Layers3 :size="15" class="text-brand" />
        <strong class="text-sm">制图产出</strong>
        <span class="rounded-full bg-surface-2 px-1.5 py-0.5 font-mono text-[11px] text-text-3">
          {{ artifacts.length }}
        </span>
      </div>
      <Button
        v-if="artifacts.length"
        variant="ghost"
        size="sm"
        class="ml-auto h-6 gap-1 px-2 text-[11px] text-text-3"
        @click="actions.clearAll()"
      >
        <Trash2 :size="12" /> 清空
      </Button>
    </div>

    <div class="min-h-0 flex-1 overflow-y-auto px-3 pb-3">
      <div v-if="!artifacts.length" class="flex h-full flex-col items-center justify-center gap-2 py-10 text-center">
        <div class="grid h-11 w-11 place-items-center rounded-xl border border-dashed border-border text-text-3">
          <MapPinned :size="20" />
        </div>
        <p class="text-[12px] font-medium text-text-2">还没有制图产出</p>
        <p class="max-w-[240px] text-[11px] leading-relaxed text-text-3">
          每次 AI 分析完成后，生成的 GeoJSON 会自动登记在这里，可定位、显隐、导出或删除。
        </p>
      </div>

      <div v-else class="flex flex-col gap-2">
        <div
          v-for="artifact in artifacts"
          :key="artifact.id"
          class="group rounded-xl border bg-surface-solid p-2.5 transition-colors"
          :class="artifact.id === activeId ? 'border-brand/50 bg-brand-soft/30' : 'border-border hover:border-brand/30'"
          @click="actions.focus(artifact.id)"
        >
          <!-- header -->
          <div class="flex items-start gap-2">
            <span
              class="mt-0.5 h-2.5 w-2.5 shrink-0 rounded-sm"
              :style="{ background: artifactColor(artifact.turnIndex) }"
            ></span>
            <div class="min-w-0 flex-1">
              <p class="truncate text-[12px] font-medium text-text" :title="artifact.label">
                {{ artifact.label }}
              </p>
              <div class="mt-0.5 flex flex-wrap items-center gap-1.5 text-[11px] text-text-3">
                <span class="rounded bg-surface-2 px-1 py-0.5 font-mono">#{{ artifact.turnIndex }}</span>
                <span>{{ artifact.featureCount }} 要素</span>
                <span class="font-mono">{{ runTag(artifact.runId) }}</span>
              </div>
            </div>
            <button
              type="button"
              class="shrink-0 rounded-md p-1 text-text-3 transition-colors hover:bg-surface-2 hover:text-text"
              :title="artifact.visible ? '隐藏图层' : '显示图层'"
              @click.stop="actions.toggleVisible(artifact)"
            >
              <Eye v-if="artifact.visible" :size="14" />
              <EyeOff v-else :size="14" />
            </button>
          </div>

          <!-- query snippet -->
          <p class="mt-1.5 truncate text-[11px] text-text-3" :title="artifact.query">
            “{{ artifact.query }}”
          </p>

          <!-- actions -->
          <div class="mt-2 flex items-center gap-1.5">
            <Button
              variant="outline" size="sm"
              class="h-6 gap-1 px-2 text-[11px]"
              :disabled="!artifact.bbox"
              @click.stop="actions.locate(artifact)"
            >
              <Crosshair :size="12" /> 定位
            </Button>
            <Button
              variant="ghost" size="sm"
              class="h-6 gap-1 px-2 text-[11px]"
              @click.stop="actions.exportGeoJson(artifact)"
            >
              <Download :size="12" /> 导出
            </Button>
            <Button
              variant="ghost" size="sm"
              class="ml-auto h-6 gap-1 px-2 text-[11px] text-text-3 hover:text-danger"
              @click.stop="actions.remove(artifact)"
            >
              <Trash2 :size="12" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Crosshair, Download, Eye, EyeOff, Layers3, MapPinned, Trash2 } from 'lucide-vue-next'
import Button from '@/components/ui/Button.vue'
import { useChatStore } from '@/stores/chatStore'
import { resultColor } from '@/core'
import { useArtifactActions } from './useArtifactActions'

const chatStore = useChatStore()
const actions = useArtifactActions()

const artifacts = computed(() => chatStore.artifacts.items)
const activeId = computed(() => chatStore.artifacts.activeId)

const runTag = (runId: string) => (runId ? runId.slice(0, 6) : '—')
const artifactColor = (turnIndex: number) => {
  const c = resultColor(turnIndex)
  return `rgba(${c[0]}, ${c[1]}, ${c[2]}, ${(c[3] / 255).toFixed(2)})`
}
</script>
