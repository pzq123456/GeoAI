<template>
  <div class="flex h-full min-h-0 flex-col">
    <!-- Header -->
    <header class="flex shrink-0 items-center justify-between px-4 pb-2 pt-3">
      <div class="flex min-w-0 items-center gap-2">
        <span
          class="h-2 w-2 shrink-0 rounded-full bg-text-3 transition-colors"
          :class="isTyping ? '!bg-brand ring-4 ring-brand/15' : ''"
        ></span>
        <strong class="text-sm">Agent</strong>
        <small v-if="runId" class="rounded-full border border-border px-1.5 py-0.5 font-mono text-[11px] text-text-3">
          {{ runId.slice(0, 8) }}
        </small>
      </div>
      <Button v-if="messages.length > 1" variant="ghost" size="sm" class="h-6 px-2 text-xs" @click="clearChat">
        清空
      </Button>
    </header>

    <!-- Tabs -->
    <div class="flex shrink-0 gap-1 border-b border-border px-3 pb-0">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        type="button"
        class="relative flex items-center gap-1.5 px-2.5 pb-2 pt-1 text-[12px] font-medium transition-colors"
        :class="activeTab === tab.key ? 'text-brand' : 'text-text-3 hover:text-text-2'"
        @click="activeTab = tab.key"
      >
        <component :is="tab.icon" :size="13" />
        {{ tab.label }}
        <span v-if="tab.key === 'trace' && steps.length" class="rounded-full bg-surface-2 px-1 font-mono text-[10px] text-text-3">
          {{ steps.length }}
        </span>
        <span v-if="tab.key === 'artifacts' && artifacts.length" class="rounded-full bg-brand-soft px-1 font-mono text-[10px] text-brand">
          {{ artifacts.length }}
        </span>
        <span v-if="activeTab === tab.key" class="absolute inset-x-1 -bottom-px h-0.5 rounded-full bg-brand"></span>
      </button>
    </div>

    <!-- Conversation tab -->
    <div v-show="activeTab === 'chat'" ref="chatRef" class="min-h-0 flex-1 overflow-y-auto px-3.5 pb-2 pt-2">
      <ChatMessageRow
        v-for="message in messages"
        :key="message.id"
        :message="message"
        @copy="handleCopy"
        @show-trace="activeTab = 'trace'"
      />
      <!-- inline trace for the active run, always visible at the bottom of the thread -->
      <div v-if="steps.length" class="mt-2 rounded-xl border border-border bg-surface-2/50 p-2.5">
        <AgentTrace :steps="steps" :is-running="isTyping" />
      </div>
    </div>

    <!-- Trace tab -->
    <div v-show="activeTab === 'trace'" class="min-h-0 flex-1 overflow-y-auto px-3.5 pb-2 pt-3">
      <AgentTrace :steps="steps" :is-running="isTyping" />
      <div v-if="!steps.length" class="mt-3 text-center text-[11px] text-text-3">
        发起一次分析后，工具调用链路会显示在这里。
      </div>
    </div>

    <!-- Artifacts tab -->
    <div v-show="activeTab === 'artifacts'" class="min-h-0 flex-1 overflow-hidden">
      <ArtifactPanel />
    </div>

    <!-- Composer -->
    <footer class="shrink-0 border-t border-border px-3.5 pb-3 pt-2.5">
      <div class="flex gap-1.5 overflow-x-auto pb-2">
        <button
          v-for="task in quickTasks"
          :key="task.label"
          type="button"
          class="shrink-0 whitespace-nowrap rounded-full border border-border bg-surface-2 px-2.5 py-1 text-[11px] text-text-2 transition-colors hover:border-brand hover:text-brand disabled:cursor-default disabled:opacity-50"
          :disabled="isTyping"
          @click="runTask(task.query)"
        >{{ task.label }}</button>
      </div>

      <div v-if="isTyping" class="flex items-center gap-2 pb-2 pt-0.5 text-[11px] text-text-2">
        <Loader2 :size="12" class="animate-spin text-brand" />{{ currentStatus || 'Working…' }}
      </div>

      <div class="rounded-xl border border-border bg-surface-solid p-2 focus-within:border-brand/50">
        <Textarea
          ref="inputRef"
          v-model="inputMsg"
          :rows="2"
          placeholder="询问香港空间数据…"
          @keydown.enter.exact.prevent="handleSend"
        />
        <div class="mt-1.5 flex items-center justify-between">
          <span v-if="selectedRegion" class="cursor-pointer text-[11px] text-brand" @click="clearSelection">
            ◎ {{ selectedRegion.properties?.name || 'Selected' }} ×
          </span>
          <span v-else class="text-[11px] text-text-3">Enter 发送 · 基于 {{ artifacts.length ? artifacts.length + ' 轮产出' : '香港开放数据' }}</span>
          <Button
            variant="default"
            size="icon"
            class="h-7 w-7 rounded-lg"
            :disabled="!inputMsg.trim() || isTyping"
            @click="handleSend"
          >
            <ArrowUp :size="14" />
          </Button>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { ArrowUp, Layers3, ListTree, Loader2, MessagesSquare } from 'lucide-vue-next'
import ChatMessageRow from './ChatMessageRow.vue'
import AgentTrace from './AgentTrace.vue'
import ArtifactPanel from './ArtifactPanel.vue'
import { useChatLogic } from './useChatLogic'
import { useChatStore } from '@/stores/chatStore'

import Button from '@/components/ui/Button.vue'
import Textarea from '@/components/ui/Textarea.vue'
import { toast } from '@/components/ui/useToast'

const emit = defineEmits<{ 'refresh-map': [] }>()
const chatStore = useChatStore()
const {
  isTyping, currentStatus, selectedRegion, clearSelection, clearChat, sendMessage, artifacts,
} = useChatLogic(emit)

const tabs = [
  { key: 'chat', label: '对话', icon: MessagesSquare },
  { key: 'trace', label: '链路', icon: ListTree },
  { key: 'artifacts', label: '产出', icon: Layers3 },
] as const
type TabKey = (typeof tabs)[number]['key']
const activeTab = ref<TabKey>('chat')

const messages = computed(() => chatStore.messages)
const runId = computed(() => chatStore.messages.at(-1)?.runId)
/** Trace of the active (last) run. */
const steps = computed(() => {
  const last = chatStore.run
  if (!last || !last.steps.length) return []
  return last.steps.map((s) => ({
    id: s.id,
    kind: s.kind,
    title: s.title,
    callId: s.callId,
    detail: s.detail,
    sequence: s.sequence,
    status: s.status,
    latencyMs: s.latencyMs,
    retryable: s.retryable,
    timestamp: s.timestamp,
  }))
})

const inputMsg = ref('')
const inputRef = ref<{ focus: () => void } | null>(null)
const chatRef = ref<HTMLElement | null>(null)

const quickTasks = [
  { label: '查找医院', query: '在 hk-health 图层中查找医院' },
  { label: '800m 邻近分析', query: '对 hk-health 图层做 800m 范围邻近查询并计算凸包' },
  { label: '学校分布', query: '分析 hk-education 图层中学校的空间分布' },
]

const scrollToBottom = async () => {
  await nextTick()
  if (chatRef.value) chatRef.value.scrollTop = chatRef.value.scrollHeight
}

watch(() => messages.value.length, scrollToBottom)
watch(() => messages.value.at(-1)?.content, () => { void scrollToBottom() })
watch(() => chatStore.draft, (value) => {
  if (!value) return
  inputMsg.value = value
  chatStore.draft = ''
  activeTab.value = 'chat'
  nextTick(() => inputRef.value?.focus())
})

const handleCopy = async (text: string) => {
  try {
    await navigator.clipboard.writeText(text)
    toast.success('已复制', { duration: 900 })
  } catch {
    toast.error('复制失败')
  }
}

const runTask = async (query: string) => {
  if (!query || isTyping.value) return
  inputMsg.value = ''
  activeTab.value = 'chat'
  await sendMessage(query)
}

const handleSend = () => {
  const query = inputMsg.value.trim()
  if (!query) return
  void runTask(query)
}
</script>
