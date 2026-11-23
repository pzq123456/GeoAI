/**
 * SSE transport adapter. The only place that knows about `fetch`, `data: `
 * frames and legacy v0 payloads; it emits framework-free `AgentEvent`s.
 */

import type { AgentEvent, AgentRequest, AgentTransport } from '@/core'

export class SseAgentTransport implements AgentTransport {
  private controller: AbortController | null = null

  constructor(private readonly endpoint = 'http://localhost:8000/api/chat') {}

  abort(): void {
    this.controller?.abort()
    this.controller = null
  }

  async *stream(req: AgentRequest): AsyncIterable<AgentEvent> {
    this.controller = new AbortController()
    const response = await fetch(this.endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query: req.query,
        history: req.history ?? [],
        context: req.context ?? {},
      }),
      signal: this.controller.signal,
    })

    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`)
    if (!response.body) throw new Error('Response body is empty')

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    try {
      for (;;) {
        const { value, done } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        for (const frame of takeFrames(buffer)) {
          const event = parseFrame(frame)
          if (event) yield event
        }
        buffer = tailBuffer(buffer)
      }
      buffer += decoder.decode()
      if (buffer.trim()) {
        const event = parseFrame(buffer)
        if (event) yield event
      }
    } catch (err) {
      if ((err as Error).name === 'AbortError') return
      throw err
    } finally {
      try { await reader.cancel() } catch { /* stream already closed */ }
    }
  }
}

/** Split complete `data: ...\n\n` frames, returning only the frame bodies. */
function takeFrames(buffer: string): string[] {
  const parts = buffer.split('\n\n')
  parts.pop() // keep the incomplete tail in the caller's buffer
  return parts
}

function tailBuffer(buffer: string): string {
  const parts = buffer.split('\n\n')
  return parts.pop() ?? ''
}

/** Parse one SSE frame with double-JSON tolerance and legacy normalisation. */
export function parseFrame(frame: string): AgentEvent | null {
  const line = frame
    .split(/\r?\n/)
    .map((part) => part.trim())
    .find((part) => part.startsWith('data:'))
  if (!line) return null

  let raw = line.slice('data:'.length).trim()
  if (!raw) return null

  try {
    let parsed: unknown = JSON.parse(raw)
    // Some legacy frames double-encode the JSON payload as a string.
    if (typeof parsed === 'string') {
      try { parsed = JSON.parse(parsed) } catch { /* keep original string */ }
    }
    return normalizeLegacy(parsed) as AgentEvent
  } catch (err) {
    console.error('解析 SSE 数据失败。Raw:', raw, 'Error:', err)
    return null
  }
}

/** Accept legacy v0 frames during migration; new backend emits only v1. */
export function normalizeLegacy(parsed: unknown): unknown {
  if (typeof parsed !== 'object' || parsed === null) return parsed
  const value = parsed as Record<string, unknown>
  if (value.type === 'final_result') {
    return { ...value, type: 'final', result: value.data }
  }
  if (value.type === 'status' && typeof value.data === 'string') {
    return { ...value, message: value.data }
  }
  if (value.type === 'error' && typeof value.data === 'string') {
    return { ...value, message: value.data }
  }
  if (value.type === 'error' && typeof value.data === 'object' && value.data !== null) {
    const data = value.data as { message?: string }
    if (data.message) return { ...value, message: data.message }
  }
  return parsed
}
