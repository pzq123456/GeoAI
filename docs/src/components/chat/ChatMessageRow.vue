<template>
  <div class="flex w-full gap-2.5 py-1.5" :class="message.role === 'user' ? 'flex-row-reverse' : ''">
    <div class="shrink-0 pt-0.5">
      <Avatar size="sm">
        <Bot v-if="isAI" :size="14" class="text-brand" />
        <User v-else :size="14" />
      </Avatar>
    </div>

    <div class="flex min-w-0 max-w-[calc(100%-38px)] flex-col" :class="message.role === 'user' ? 'items-end' : ''">
      <div class="mb-1 flex flex-wrap items-center gap-1.5" :class="message.role === 'user' ? 'justify-end' : ''">
        <span class="text-[11px] font-bold uppercase tracking-wider text-text-3">
          {{ isAI ? 'Agent' : 'You' }}
        </span>
        <span v-if="message.contextLabel" class="max-w-[180px] truncate rounded-full border border-brand/20 bg-brand-soft px-1.5 py-0.5 text-[11px] text-brand">
          ◎ {{ message.contextLabel }}
        </span>
        <span v-if="message.runId" class="rounded-full border border-border bg-surface-2 px-1.5 py-0.5 font-mono text-[11px] text-text-3">
          {{ message.runId.slice(0, 8) }}
        </span>
        <span v-if="message.status === 'streaming'" class="rounded-full border border-brand/20 px-1.5 py-0.5 text-[11px] text-brand">
          live
        </span>
      </div>

      <div
        class="break-words rounded-[10px] border border-border bg-surface-solid px-3 py-2 text-[13px] leading-relaxed text-text"
        :class="isAI ? 'rounded-tl-sm' : 'rounded-tr-sm border-brand/20 bg-brand-soft'"
      >
        <template v-if="isAI">
          <MarkdownRender v-if="message.content" :content="message.content" />
          <div v-else class="flex h-[18px] items-center gap-1">
            <span
              v-for="n in 3"
              :key="n"
              class="h-1.5 w-1.5 animate-bounce rounded-full bg-brand"
              :style="{ animationDelay: `${(n - 3) * 0.16}s` }"
            ></span>
          </div>
        </template>
        <template v-else>{{ message.content }}</template>
      </div>

      <!-- compact action row -->
      <div v-if="isAI && message.content" class="mt-1 flex items-center gap-2 opacity-60 transition-opacity hover:opacity-100">
        <Button
          v-if="trace.length"
          variant="link" size="sm" class="h-auto gap-1 px-0 text-[11px]"
          @click="emit('show-trace')"
        >
          <ListTree :size="12" /> 查看链路 ({{ trace.length }})
        </Button>
        <Button variant="link" size="sm" class="h-auto gap-1 px-0 text-[11px]" @click="emit('copy', message.content)">
          <Copy :size="12" /> 复制
        </Button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import MarkdownRender from 'markstream-vue'
import 'markstream-vue/index.css'
import { Bot, Copy, ListTree, User } from 'lucide-vue-next'
import type { ChatMessage, TraceEntry } from '@/types'

import Avatar from '@/components/ui/Avatar.vue'
import Button from '@/components/ui/Button.vue'

const props = defineProps<{ message: ChatMessage }>()
const emit = defineEmits<{ copy: [content: string]; 'show-trace': [] }>()

const isAI = computed(() => props.message.role === 'ai')
const trace = computed<TraceEntry[]>(() => props.message.trace ?? [])
</script>
