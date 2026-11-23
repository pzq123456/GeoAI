/** Shared frontend types for GeoAI SSE events and GeoJSON payloads. */

// Geometry primitives live in the framework-free core; re-exported here so
// existing `@/types` imports keep working unchanged.
import type { GeoJsonFeature, FeatureCollection } from '@/core'
export type { GeoJsonFeature, FeatureCollection, BBox, RGBAColor } from '@/core'

export interface ChatReport {
  analysis_steps?: string[]
  final_report?: string
  visualization_status?: string
  guidance?: string
  suggestions?: string[]
}

export interface FinalResultData {
  report: ChatReport
  geojson: FeatureCollection | null
  new_history: unknown[]
}

// Event contract is generated from the backend Pydantic models.
// DO NOT hand-write SSE event types here.
export type {
  AgentEventSchema as AgentEvent,
  StatusEvent as AgentStatusEvent,
  ToolCallEvent,
  ToolResultEvent,
  FinalEvent as AgentFinalEvent,
  ErrorEvent as AgentErrorEvent,
} from './agent-events.generated'

/** One step inside a message's inline execution trace. */
export interface TraceEntry {
  id: string
  kind: 'status' | 'tool_call' | 'tool_result' | 'final' | 'error'
  title: string
  /** Caller's call_id (tool_call ↔ tool_result pairing). */
  callId?: string
  detail?: string
  sequence: number
  status?: 'success' | 'error'
  latencyMs?: number
  retryable?: boolean
  timestamp: number
}

export interface ChatMessage {
  id: string
  role: 'ai' | 'user'
  content: string
  createdAt: number
  status?: 'streaming' | 'complete' | 'error'
  /** The execution trace lives on the message — no separate Trace page. */
  trace?: TraceEntry[]
  runId?: string
  /** Human-readable snapshot of the map context attached to this turn. */
  contextLabel?: string
}

export interface FinalPayload {
  report: ChatReport
  history: unknown[]
  run_id?: string
}

export interface ChatHandlers {
  onStatus?: (message: string) => void
  onToolCall?: (event: import('./agent-events.generated').ToolCallEvent) => void
  onToolResult?: (event: import('./agent-events.generated').ToolResultEvent) => void
  onGeoJson?: (geojson: FeatureCollection) => void
  onFinal?: (payload: FinalPayload) => void
  onError?: (error: Error) => void
}
