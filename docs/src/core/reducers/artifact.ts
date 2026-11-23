/**
 * Pure reducer for AI cartographic outputs. No framework dependencies.
 */

import {
  bboxOf,
  createArtifactState,
  defaultArtifactLabel,
  type AgentArtifact,
  type ArtifactEvent,
  type ArtifactState,
} from '../model/artifact'
import type { FeatureCollection } from '../model/geo'

export function artifactsReducer(state: ArtifactState, event: ArtifactEvent): ArtifactState {
  switch (event.type) {
    case 'add': {
      if (!event.geojson || !Array.isArray(event.geojson.features) || event.geojson.features.length === 0) {
        return state
      }
      const seq = state.seq + 1
      const artifact: AgentArtifact = {
        id: `artifact-${seq}`,
        runId: event.runId,
        turnIndex: seq,
        query: event.query,
        label: defaultArtifactLabel(event.query, seq),
        geojson: event.geojson as FeatureCollection,
        createdAt: event.createdAt ?? Date.now(),
        featureCount: event.geojson.features.length,
        bbox: event.bbox ?? bboxOf(event.geojson),
        visible: true,
        layerId: `agent-result-${seq}`,
      }
      return { items: [...state.items, artifact], seq, activeId: artifact.id }
    }

    case 'toggleVisible':
      return {
        ...state,
        items: state.items.map((item) =>
          item.id === event.id ? { ...item, visible: !item.visible } : item,
        ),
      }

    case 'setVisible':
      return {
        ...state,
        items: state.items.map((item) =>
          item.id === event.id ? { ...item, visible: event.visible } : item,
        ),
      }

    case 'focus':
      return { ...state, activeId: event.id }

    case 'rename':
      return {
        ...state,
        items: state.items.map((item) =>
          item.id === event.id ? { ...item, label: event.label } : item,
        ),
      }

    case 'remove': {
      const items = state.items.filter((item) => item.id !== event.id)
      return {
        ...state,
        items,
        activeId: state.activeId === event.id ? (items.at(-1)?.id ?? null) : state.activeId,
      }
    }

    case 'clear':
      return createArtifactState()

    default:
      return state
  }
}
