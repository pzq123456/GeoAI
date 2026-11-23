import { describe, expect, it } from 'vitest'
import { createRun, runReducer } from '@/core'

describe('runReducer', () => {
  it('tool_call appends a trace step carrying call_id', () => {
    const running = runReducer(createRun('run-1'), { type: 'start', runId: 'run-1' })
    const next = runReducer(running, {
      type: 'tool_call',
      toolName: 'find_tree',
      callId: 'call-1',
      args: { id: 'T03562' },
    })

    expect(next.runId).toBe('run-1')
    expect(next.steps).toHaveLength(1)
    expect(next.steps[0]).toMatchObject({
      kind: 'tool_call',
      title: 'find_tree',
      callId: 'call-1',
      detail: JSON.stringify({ id: 'T03562' }),
      sequence: 1,
    })
  })

  it('tool_result patches the matching call without appending', () => {
    let run = runReducer(createRun(), { type: 'start' })
    run = runReducer(run, { type: 'tool_call', toolName: 'geo', callId: 'call-9' })
    const next = runReducer(run, {
      type: 'tool_result',
      callId: 'call-9',
      status: 'success',
      latencyMs: 42,
      detail: 'ok',
    })

    expect(next.steps).toHaveLength(1)
    expect(next.steps[0]).toMatchObject({
      status: 'success',
      latencyMs: 42,
      detail: 'ok',
    })
    expect(run.steps[0].status).toBeUndefined() // original is immutable
  })

  it('final sets content, history, status and adds a final step', () => {
    const running = runReducer(createRun(), { type: 'start' })
    const next = runReducer(running, {
      type: 'final',
      report: { final_report: 'Done.' },
      history: [{ role: 'user' }],
      runId: 'run-final',
    })

    expect(next.status).toBe('complete')
    expect(next.content).toBe('Done.')
    expect(next.history).toEqual([{ role: 'user' }])
    expect(next.runId).toBe('run-final')
    expect(next.steps.at(-1)?.kind).toBe('final')
  })

  it('error records the failure and stops streaming', () => {
    const running = runReducer(createRun(), { type: 'start' })
    const next = runReducer(running, { type: 'error', message: 'boom' })
    expect(next.status).toBe('error')
    expect(next.error).toBe('boom')
    expect(next.currentStatus).toBe('')
    expect(next.steps.at(-1)?.kind).toBe('error')
  })
})
