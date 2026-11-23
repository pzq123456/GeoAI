/** Framework-free agent-run model (the state behind the chat transcript). */

export type RunStatus = 'idle' | 'running' | 'complete' | 'error'

export type TraceStepKind = 'status' | 'tool_call' | 'tool_result' | 'final' | 'error'

export interface TraceStep {
  id: string
  kind: TraceStepKind
  title: string
  /** Pairs a `tool_call` with its `tool_result`. */
  callId?: string
  detail?: string
  sequence: number
  status?: 'success' | 'error'
  latencyMs?: number
  retryable?: boolean
  timestamp: number
}

export interface AgentRun {
  runId?: string
  status: RunStatus
  /** Final answer text (mirrors the active ChatMessage.content). */
  content: string
  currentStatus: string
  steps: TraceStep[]
  history: unknown[]
  error?: string
}

/** Events consumed by `runReducer`. Superset of the SSE `AgentEvent` union. */
export type RunEvent =
  | { type: 'start'; runId?: string }
  | { type: 'status'; message: string; runId?: string; timestamp?: number }
  | {
      type: 'tool_call'
      toolName: string
      callId: string
      args?: unknown
      runId?: string
      timestamp?: number
    }
  | {
      type: 'tool_result'
      callId: string
      status: 'success' | 'error'
      latencyMs?: number
      detail?: string
      retryable?: boolean
    }
  | {
      type: 'trace'
      step: Omit<TraceStep, 'id' | 'sequence' | 'timestamp'> & { timestamp?: number }
    }
  | {
      type: 'patch_trace'
      callId: string
      patch: Partial<Pick<TraceStep, 'status' | 'latencyMs' | 'detail' | 'retryable'>>
    }
  | { type: 'content'; content: string }
  | { type: 'run_id'; runId: string }
  | { type: 'history'; history: unknown[] }
  | { type: 'complete' }
  | { type: 'error'; message: string; content?: string; timestamp?: number }
  | {
      type: 'final'
      report?: { final_report?: string; guidance?: string }
      history?: unknown[]
      runId?: string
      timestamp?: number
    }
  | { type: 'reset' }

/** Normalised SSE event emitted by the agent transport (core-owned type). */
export type AgentEvent =
  | { type: 'status'; message: string; run_id?: string; stage?: string | null }
  | {
      type: 'tool_call'
      tool_name: string
      call_id: string
      arguments?: Record<string, unknown>
      run_id?: string
    }
  | {
      type: 'tool_result'
      tool_name: string
      call_id: string
      status: 'success' | 'error'
      latency_ms: number
      result_ref?: string | null
      error?: { code: string; message: string; retryable?: boolean } | null
      run_id?: string
    }
  | { type: 'final'; result?: Record<string, unknown>; run_id?: string }
  | { type: 'error'; code?: string; message: string; retryable?: boolean; run_id?: string }

export interface AgentRequest {
  query: string
  history?: unknown[]
  context?: Record<string, unknown>
}

export function createRun(runId?: string): AgentRun {
  return {
    runId,
    status: 'idle',
    content: '',
    currentStatus: '',
    steps: [],
    history: [],
  }
}
