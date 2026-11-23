/**
 * Framework-free model for AI cartographic outputs.
 *
 * One `AgentArtifact` is the GeoJSON produced by one completed agent turn.
 * Keeping these in core (not Vue/Pinia) means multi-turn intermediate results
 * can be reduced/tested/replayed without a UI shell.
 */

import type { BBox, FeatureCollection } from './geo'

export interface AgentArtifact {
  id: string
  /** Agent run this output came from. */
  runId: string
  /** 1-based turn index within the conversation. */
  turnIndex: number
  /** The user query that triggered this output. */
  query: string
  /** Human label shown in the outputs panel. */
  label: string
  geojson: FeatureCollection
  createdAt: number
  featureCount: number
  bbox: BBox | null
  /** Whether the result layer is currently shown on the map. */
  visible: boolean
  /** Scene layer id used by the map adapter. */
  layerId: string
}

export interface ArtifactState {
  items: AgentArtifact[]
  /** Auto-incrementing counter for stable ids / turn numbering. */
  seq: number
  /** Currently focused artifact (drives highlight + detail view). */
  activeId: string | null
}

export type ArtifactEvent =
  | {
      type: 'add'
      runId: string
      query: string
      geojson: FeatureCollection
      bbox?: BBox | null
      createdAt?: number
    }
  | { type: 'toggleVisible'; id: string }
  | { type: 'setVisible'; id: string; visible: boolean }
  | { type: 'focus'; id: string | null }
  | { type: 'rename'; id: string; label: string }
  | { type: 'remove'; id: string }
  | { type: 'clear' }

export function createArtifactState(): ArtifactState {
  return { items: [], seq: 0, activeId: null }
}

export function artifactLayerId(index: number): string {
  return `agent-result-${index}`
}

/** Compute a WGS84 bbox from a feature collection, or null when empty. */
export function bboxOf(geojson: FeatureCollection): BBox | null {
  let minX = Infinity
  let minY = Infinity
  let maxX = -Infinity
  let maxY = -Infinity

  const visit = (value: unknown): void => {
    if (!Array.isArray(value)) return
    if (typeof value[0] === 'number' && typeof value[1] === 'number') {
      minX = Math.min(minX, value[0])
      minY = Math.min(minY, value[1])
      maxX = Math.max(maxX, value[0])
      maxY = Math.max(maxY, value[1])
      return
    }
    value.forEach(visit)
  }

  for (const feature of geojson.features ?? []) {
    visit((feature.geometry as { coordinates?: unknown } | null)?.coordinates)
  }
  if (minX === Infinity) return null
  return [minX, minY, maxX, maxY]
}

export function defaultArtifactLabel(query: string, turnIndex: number): string {
  const trimmed = query.trim().replace(/\s+/g, ' ')
  const short = trimmed.length > 24 ? `${trimmed.slice(0, 24)}…` : trimmed
  return `产出 ${turnIndex} · ${short || '未命名'}`
}
