import { computed, type ComputedRef } from 'vue'
import { useMapStore } from '@/stores/mapStore'
import { useChatStore } from '@/stores/chatStore'
import { geoAI } from '@/services/geoApi'
import {
  buildContext as coreBuildContext,
  resultToLayer,
  type AgentContext,
  type FeatureCollection,
} from '@/core'
import { buildScene } from '@/adapters/map/layerSpec'
import { createResultLayer } from '@/adapters/map/resultLayer'
import { useArtifactActions } from './useArtifactActions'
import type { GeoJsonFeature } from '@/types'

/** Kept as the exported name for the .vue caller; now the core context shape. */
export type MapContext = AgentContext

export function useChatLogic(emit: (event: 'refresh-map') => void) {
  const mapStore = useMapStore()
  const chatStore = useChatStore()
  const artifactActions = useArtifactActions()

  const selectedRegion: ComputedRef<GeoJsonFeature | null> = computed(
    () => mapStore.selectedRegion,
  )

  /** Serialisable snapshot of what the user is currently looking at. */
  const buildContext = (): MapContext =>
    coreBuildContext(
      buildScene({
        layers: mapStore.layers.layers,
        selection: mapStore.selectedRegion,
        hover: mapStore.hoveredRegion,
        viewport: {
          center: [...mapStore.viewport.center] as [number, number],
          zoom: mapStore.viewport.zoom,
          bearing: mapStore.viewport.bearing,
          pitch: mapStore.viewport.pitch,
        },
        theme: mapStore.scene.theme,
      }),
    )

  const sendMessage = async (query: string): Promise<void> => {
    if (!query || chatStore.isStreaming) return

    const context = buildContext()
    const feature = context.selectedFeature
    const label = feature
      ? String(feature.properties.name ?? feature.properties.id ?? 'Selected')
      : undefined

    chatStore.addUserMessage(query, label)
    const assistant = chatStore.addAssistantMessage()
    chatStore.currentStatus = 'Preparing…'

    /** GeoJSON may arrive before `final`; hold it until the turn completes. */
    let pendingGeoJson: FeatureCollection | null = null
    let pendingRunId = ''

    await geoAI.chat(
      { query, history: chatStore.history, context: context as unknown as Record<string, unknown> },
      {
        onStatus: (message) => {
          chatStore.currentStatus = message
          chatStore.addTrace(assistant.id, { kind: 'status', title: message })
        },
        onToolCall: (event) => {
          if (event.run_id) chatStore.setRunId(assistant.id, event.run_id)
          chatStore.addTrace(assistant.id, {
            kind: 'tool_call',
            title: event.tool_name,
            callId: event.call_id,
            detail: JSON.stringify(event.arguments ?? {}),
          })
        },
        onToolResult: (event) => {
          if (event.run_id) chatStore.setRunId(assistant.id, event.run_id)
          chatStore.patchTrace(assistant.id, event.call_id, {
            status: event.status === 'error' ? 'error' : 'success',
            latencyMs: event.latency_ms,
            detail: event.error
              ? `${event.error.code}: ${event.error.message}`
              : undefined,
            retryable: event.error?.retryable ?? false,
          })
        },
        onGeoJson: (geoData) => {
          pendingGeoJson = geoData
          // Also render immediately as a provisional result layer.
          const spec = resultToLayer({ geojson: geoData })
          if (spec) {
            mapStore.removeLayer(spec.id)
            mapStore.addLayer(createResultLayer(spec))
          }
          emit('refresh-map')
        },
        onFinal: ({ report, history, run_id }) => {
          pendingRunId = run_id ?? ''
          if (run_id) chatStore.setRunId(assistant.id, run_id)
          if (Array.isArray(history)) chatStore.setHistory(history)
          chatStore.addTrace(assistant.id, { kind: 'final', title: '分析完成' })
          chatStore.setContent(
            assistant.id,
            report?.final_report || report?.guidance || '（未收到有效报告）',
          )
          chatStore.complete(assistant.id)

          if (pendingGeoJson) {
            const state = chatStore.dispatchArtifact({
              type: 'add',
              runId: pendingRunId || assistant.id,
              query,
              geojson: pendingGeoJson,
            })
            const artifact = state.items.at(-1)
            if (artifact) {
              // Replace the provisional layer with one bound to the artifact id.
              mapStore.removeLayer('AI-Result')
              const spec = resultToLayer(
                { geojson: artifact.geojson },
                1,
                { layerId: artifact.layerId, turnIndex: artifact.turnIndex },
              )
              if (spec) mapStore.addLayer(createResultLayer(spec))
            }
            pendingGeoJson = null
          }
        },
        onError: (err) => {
          chatStore.addTrace(assistant.id, { kind: 'error', title: err.message })
          chatStore.fail(assistant.id, `❌ Error: ${err.message}`)
        },
      },
    )
  }

  return {
    isTyping: computed(() => chatStore.isStreaming),
    currentStatus: computed(() => chatStore.currentStatus),
    selectedRegion,
    clearSelection: () => mapStore.updateSelectedRegion(null),
    clearChat: () => chatStore.clear(),
    sendMessage,
    artifacts: computed(() => chatStore.artifacts.items),
    artifactActions,
  }
}
