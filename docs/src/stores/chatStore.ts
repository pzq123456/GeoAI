import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  artifactsReducer,
  createArtifactState,
  createRun,
  runReducer,
  type AgentRun,
  type ArtifactEvent,
  type ArtifactState,
  type RunEvent,
  type TraceStep,
} from '@/core'
import type { ChatMessage, TraceEntry } from '@/types'

let counter = 0
const nextId = (prefix: string) => `${prefix}-${Date.now().toString(36)}-${++counter}`

function toTraceEntry(step: TraceStep): TraceEntry {
  return {
    id: step.id,
    kind: step.kind,
    title: step.title,
    callId: step.callId,
    detail: step.detail,
    sequence: step.sequence,
    status: step.status,
    latencyMs: step.latencyMs,
    retryable: step.retryable,
    timestamp: step.timestamp,
  }
}

export const useChatStore = defineStore('chat', () => {
  const messages = ref<ChatMessage[]>([
    {
      id: 'welcome',
      role: 'ai',
      content: '已就绪。我可以检索香港开放数据（环境、医疗、教育、体育、公共服务、Wi-Fi 等），执行空间邻近与凸包分析，并把每轮结果保存为制图产出。试着问一个问题吧。',
      createdAt: Date.now(),
      status: 'complete',
    },
  ])
  const isStreaming = ref(false)
  const currentStatus = ref('')
  const history = ref<unknown[]>([])
  /** Shared draft so the Inspector can hand a selected feature to the chat. */
  const draft = ref('')

  /** Core run state; the messages array below is the UI-facing mirror. */
  const run = ref<AgentRun>(createRun())
  /** Multi-turn cartographic outputs (core-owned, reducer-driven). */
  const artifacts = ref<ArtifactState>(createArtifactState())
  let activeId: string | null = null

  const findMessage = (id: string) => messages.value.find((m) => m.id === id)

  /** Single transition point: runReducer → mirror into ChatMessage / refs. */
  const dispatch = (event: RunEvent) => {
    const previous = run.value
    const next = runReducer(previous, event)
    run.value = next

    const message = activeId ? findMessage(activeId) : undefined
    if (message) {
      message.content = next.content
      message.runId = next.runId
      message.status =
        next.status === 'running'
          ? 'streaming'
          : next.status === 'idle'
            ? undefined
            : next.status
      message.trace = next.steps.map(toTraceEntry)
    }

    isStreaming.value = next.status === 'running'
    currentStatus.value = next.currentStatus
    if (next.history !== previous.history) history.value = next.history
  }

  const addUserMessage = (content: string, contextLabel?: string): ChatMessage => {
    const message: ChatMessage = {
      id: nextId('user'),
      role: 'user',
      content,
      createdAt: Date.now(),
      status: 'complete',
      contextLabel,
    }
    messages.value.push(message)
    return message
  }

  const addAssistantMessage = (runId?: string): ChatMessage => {
    const message: ChatMessage = {
      id: nextId('ai'),
      role: 'ai',
      content: '',
      createdAt: Date.now(),
      status: 'streaming',
      runId,
      trace: [],
    }
    messages.value.push(message)
    activeId = message.id
    dispatch({ type: 'start', runId })
    return message
  }

  const appendContent = (id: string, delta: string) => {
    if (id === activeId) dispatch({ type: 'content', content: run.value.content + delta })
    else {
      const message = findMessage(id)
      if (message) message.content += delta
    }
  }

  const setContent = (id: string, content: string) => {
    if (id === activeId) dispatch({ type: 'content', content })
    else {
      const message = findMessage(id)
      if (message) message.content = content
    }
  }

  const setRunId = (id: string, runId: string) => {
    if (id === activeId) dispatch({ type: 'run_id', runId })
    else {
      const message = findMessage(id)
      if (message) message.runId = runId
    }
  }

  const complete = (id: string) => {
    if (id === activeId) dispatch({ type: 'complete' })
    else {
      const message = findMessage(id)
      if (message) message.status = 'complete'
      isStreaming.value = false
      currentStatus.value = ''
    }
  }

  const fail = (id: string, content: string) => {
    if (id === activeId) dispatch({ type: 'error', message: content, content })
    else {
      const message = findMessage(id)
      if (message) {
        message.content = content
        message.status = 'error'
      }
      isStreaming.value = false
      currentStatus.value = ''
    }
  }

  const addTrace = (messageId: string, entry: Omit<TraceEntry, 'id' | 'timestamp' | 'sequence'>) => {
    if (messageId === activeId) {
      dispatch({
        type: 'trace',
        step: {
          kind: entry.kind,
          title: entry.title,
          callId: entry.callId,
          detail: entry.detail,
          status: entry.status,
          latencyMs: entry.latencyMs,
          retryable: entry.retryable,
        },
      })
      return
    }
    const message = findMessage(messageId)
    if (!message) return
    message.trace ??= []
    message.trace.push({
      ...entry,
      id: nextId('trace'),
      sequence: message.trace.length + 1,
      timestamp: Date.now(),
    })
  }

  /** tool_result events carry the same call_id as their tool_call. */
  const patchTrace = (
    messageId: string,
    callId: string,
    patch: Partial<Pick<TraceEntry, 'status' | 'latencyMs' | 'detail' | 'retryable'>>,
  ) => {
    if (messageId === activeId) {
      dispatch({ type: 'patch_trace', callId, patch })
      return
    }
    const entry = findMessage(messageId)?.trace?.find((t) => t.callId === callId)
    if (entry) Object.assign(entry, patch)
  }

  const setHistory = (next: unknown[]) => {
    if (Array.isArray(next)) dispatch({ type: 'history', history: next })
  }

  /** Single transition point for the artifact reducer. */
  const dispatchArtifact = (event: ArtifactEvent): ArtifactState => {
    const next = artifactsReducer(artifacts.value, event)
    artifacts.value = next
    return next
  }

  const clear = () => {
    messages.value = []
    activeId = null
    history.value = []
    run.value = createRun()
    artifacts.value = createArtifactState()
    isStreaming.value = false
    currentStatus.value = ''
  }

  return {
    messages,
    isStreaming,
    currentStatus,
    history,
    draft,
    run,
    artifacts,
    dispatchArtifact,
    addUserMessage,
    addAssistantMessage,
    appendContent,
    setContent,
    setRunId,
    complete,
    fail,
    addTrace,
    patchTrace,
    setHistory,
    clear,
  }
})
