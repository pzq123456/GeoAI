/**
 * Pure agent-run reducer: folds transport/UI events into an `AgentRun`.
 * No Vue/Pinia — the chat store is a thin mirror of this state.
 */

import {
  createRun,
  type AgentRun,
  type RunEvent,
  type TraceStep,
  type TraceStepKind,
} from '../model/agent'

function appendStep(run: AgentRun, step: Omit<TraceStep, 'id' | 'sequence' | 'timestamp'> & { timestamp?: number }): AgentRun {
  const sequence = run.steps.length + 1
  const entry: TraceStep = {
    ...step,
    id: `step-${sequence}`,
    sequence,
    timestamp: step.timestamp ?? 0,
  }
  return { ...run, steps: [...run.steps, entry] }
}

function patchStep(run: AgentRun, callId: string, patch: Partial<TraceStep>): AgentRun {
  const index = run.steps.findIndex((s) => s.callId === callId)
  if (index === -1) return run
  const steps = [...run.steps]
  steps[index] = { ...steps[index], ...patch }
  return { ...run, steps }
}

function kindFromTitle(kind: TraceStepKind, title: string): string {
  return title || kind
}

export function runReducer(run: AgentRun, event: RunEvent): AgentRun {
  switch (event.type) {
    case 'start':
      return {
        ...createRun(event.runId),
        status: 'running',
        history: run.history,
      }

    case 'status':
      return appendStep(
        { ...run, currentStatus: event.message, runId: event.runId ?? run.runId },
        { kind: 'status', title: kindFromTitle('status', event.message), timestamp: event.timestamp },
      )

    case 'tool_call':
      return appendStep(
        { ...run, runId: event.runId ?? run.runId },
        {
          kind: 'tool_call',
          title: event.toolName,
          callId: event.callId,
          detail: event.args === undefined ? undefined : JSON.stringify(event.args),
          timestamp: event.timestamp,
        },
      )

    case 'tool_result':
      return patchStep(run, event.callId, {
        status: event.status,
        latencyMs: event.latencyMs,
        detail: event.detail,
        retryable: event.retryable,
      })

    case 'trace':
      return appendStep(run, event.step)

    case 'patch_trace':
      return patchStep(run, event.callId, event.patch)

    case 'content':
      return { ...run, content: event.content }

    case 'run_id':
      return { ...run, runId: event.runId }

    case 'history':
      return { ...run, history: event.history }

    case 'complete':
      return { ...run, status: 'complete', currentStatus: '' }

    case 'error':
      return appendStep(
        {
          ...run,
          status: 'error',
          error: event.message,
          currentStatus: '',
          content: event.content ?? run.content,
        },
        { kind: 'error', title: event.message, timestamp: event.timestamp },
      )

    case 'final': {
      const report = event.report ?? {}
      const content = report.final_report || report.guidance || run.content
      const withStep = appendStep(
        {
          ...run,
          content,
          status: 'complete',
          currentStatus: '',
          history: event.history ?? run.history,
          runId: event.runId ?? run.runId,
        },
        { kind: 'final', title: '分析完成', timestamp: event.timestamp },
      )
      return withStep
    }

    case 'reset':
      return createRun()

    default:
      return run
  }
}

export { createRun }
