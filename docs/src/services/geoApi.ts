import type {
  ChatHandlers,
  FeatureCollection,
  FinalResultData,
} from '@/types'
import type { AgentEvent } from '@/core'
import { SseAgentTransport } from '@/adapters/agent/SseAgentTransport'

/**
 * Backwards-compatible facade. All transport/parsing concerns now live in
 * adapters; this class only folds normalised events into the historical
 * `ChatHandlers` callbacks.
 */
export class GeoAIService {
  private readonly transport: SseAgentTransport

  constructor(private baseUrl = 'http://localhost:8000') {
    this.transport = new SseAgentTransport(`${baseUrl}/api/chat`)
  }

  async chat(
    {
      query,
      history = [],
      context = {},
    }: { query: string; history?: unknown[]; context?: Record<string, unknown> },
    handlers: ChatHandlers = {},
  ): Promise<void> {
    try {
      for await (const event of this.transport.stream({ query, history, context })) {
        this.handleMessage(event, handlers)
      }
    } catch (err) {
      handlers.onError?.(err as Error)
    }
  }

  /** Abort an in-flight chat stream (used when a new run starts). */
  abort(): void {
    this.transport.abort()
  }

  private handleMessage(event: AgentEvent, handlers: ChatHandlers): void {
    switch (event.type) {
      case 'status':
        handlers.onStatus?.(event.message)
        break
      case 'tool_call':
        handlers.onToolCall?.(event as never)
        break
      case 'tool_result':
        handlers.onToolResult?.(event as never)
        break
      case 'final': {
        const result = (event.result ?? {}) as unknown as FinalResultData
        if (result.geojson) handlers.onGeoJson?.(result.geojson as FeatureCollection)
        handlers.onFinal?.({
          report: result.report,
          history: result.new_history ?? [],
          run_id: event.run_id,
        })
        break
      }
      case 'error':
        handlers.onError?.(new Error(event.message || 'Agent 运行报错'))
        break
      default:
        console.warn('未知事件类型:', event)
    }
  }
}

export const geoAI = new GeoAIService()
