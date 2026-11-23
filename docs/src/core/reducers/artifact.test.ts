import { describe, expect, it } from 'vitest'
import { artifactsReducer } from './artifact'
import { bboxOf, createArtifactState, type ArtifactState } from '../model/artifact'
import type { FeatureCollection } from '../model/geo'

const fc = (n: number): FeatureCollection => ({
  type: 'FeatureCollection',
  features: Array.from({ length: n }, (_, i) => ({
    type: 'Feature' as const,
    id: `f-${i}`,
    geometry: {
      type: 'Point',
      coordinates: [114 + i * 0.01, 22 + i * 0.01],
    },
    properties: { name: `F${i}` },
  })),
})

const add = (state: ArtifactState, overrides: Partial<Parameters<typeof artifactsReducer>[1]> = {}) =>
  artifactsReducer(state, {
    type: 'add',
    runId: 'run-1',
    query: '查询医院',
    geojson: fc(3),
    createdAt: 1000,
    ...overrides,
  } as Parameters<typeof artifactsReducer>[1])

describe('artifactsReducer', () => {
  it('adds an artifact with computed metadata and focuses it', () => {
    const state = add(createArtifactState())
    expect(state.items).toHaveLength(1)
    expect(state.seq).toBe(1)
    expect(state.activeId).toBe('artifact-1')
    const a = state.items[0]
    expect(a.turnIndex).toBe(1)
    expect(a.featureCount).toBe(3)
    expect(a.layerId).toBe('agent-result-1')
    expect(a.bbox).toEqual([114, 22, 114.02, 22.02])
    expect(a.visible).toBe(true)
  })

  it('assigns incrementing ids / layer ids across turns', () => {
    let state = add(createArtifactState())
    state = add(state, { runId: 'run-2', query: '另一查询' })
    expect(state.items.map((a) => a.layerId)).toEqual(['agent-result-1', 'agent-result-2'])
    expect(state.items.map((a) => a.turnIndex)).toEqual([1, 2])
  })

  it('ignores empty feature collections', () => {
    const state = artifactsReducer(createArtifactState(), {
      type: 'add',
      runId: 'r',
      query: 'q',
      geojson: fc(0),
    })
    expect(state.items).toHaveLength(0)
    expect(state.seq).toBe(0)
  })

  it('toggles and sets visibility immutably', () => {
    const state = add(createArtifactState())
    const toggled = artifactsReducer(state, { type: 'toggleVisible', id: 'artifact-1' })
    expect(toggled.items[0].visible).toBe(false)
    expect(state.items[0].visible).toBe(true)
    const forced = artifactsReducer(state, { type: 'setVisible', id: 'artifact-1', visible: false })
    expect(forced.items[0].visible).toBe(false)
  })

  it('removes an artifact and reassigns focus', () => {
    let state = add(createArtifactState())
    state = add(state, { runId: 'r2' })
    expect(state.items).toHaveLength(2)
    const removed = artifactsReducer(state, { type: 'remove', id: 'artifact-2' })
    expect(removed.items).toHaveLength(1)
    expect(removed.activeId).toBe('artifact-1')
  })

  it('renames and clears', () => {
    let state = add(createArtifactState())
    state = artifactsReducer(state, { type: 'rename', id: 'artifact-1', label: '我的产出' })
    expect(state.items[0].label).toBe('我的产出')
    state = artifactsReducer(state, { type: 'clear' })
    expect(state.items).toHaveLength(0)
  })
})

describe('bboxOf', () => {
  it('returns null for an empty collection', () => {
    expect(bboxOf(fc(0))).toBeNull()
  })
})
