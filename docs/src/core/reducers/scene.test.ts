import { describe, expect, it } from 'vitest'
import {
  createEmptyScene,
  sceneReducer,
  type GeoJsonFeature,
  type LayerSpec,
  type SceneState,
} from '@/core'

const feature = (id: string | number): GeoJsonFeature => ({
  type: 'Feature',
  id,
  geometry: { type: 'Point', coordinates: [114, 22] },
  properties: { name: `F-${id}` },
})

const spec = (id: string, role: LayerSpec['role'] = 'base'): LayerSpec => ({
  id,
  role,
  source: { kind: 'geojson', features: [] },
  style: { color: [1, 2, 3, 255] },
  visible: true,
  opacity: 1,
  order: 0,
  revision: 1,
})

function seeded(): SceneState {
  return sceneReducer(createEmptyScene(), {
    type: 'replaceLayers',
    specs: [spec('base'), spec('Highlight-Layer', 'selection')],
  })
}

describe('sceneReducer', () => {
  it('selectFeature stores the feature and updates singleton selection layers', () => {
    const state = seeded()
    const next = sceneReducer(state, { type: 'selectFeature', feature: feature('a') })

    expect(next).not.toBe(state)
    expect(next.selection?.id).toBe('a')
    expect(next.layers['Highlight-Layer'].source).toEqual({
      kind: 'geojson',
      features: [feature('a')],
    })
    expect(next.layers['Highlight-Layer'].revision).toBe(2)
    // Other layers are untouched.
    expect(next.layers.base).toEqual(state.layers.base)
  })

  it('selectFeature is a no-op for the same feature', () => {
    const once = sceneReducer(seeded(), { type: 'selectFeature', feature: feature('a') })
    const twice = sceneReducer(once, { type: 'selectFeature', feature: feature('a') })
    expect(twice).toBe(once)
  })

  it('setLayerVisibility toggles visibility and bumps revision only when changed', () => {
    const state = seeded()
    const hidden = sceneReducer(state, { type: 'setLayerVisibility', id: 'base', visible: false })
    expect(hidden.layers.base.visible).toBe(false)
    expect(hidden.layers.base.revision).toBe(2)
    expect(sceneReducer(hidden, { type: 'setLayerVisibility', id: 'base', visible: false })).toBe(hidden)
  })

  it('upsertLayer inserts new layers and merges existing ones', () => {
    const state = seeded()
    const added = sceneReducer(state, { type: 'upsertLayer', spec: spec('new', 'result') })
    expect(added.order).toEqual(['base', 'Highlight-Layer', 'new'])
    expect(added.layers.new.role).toBe('result')

    const merged = sceneReducer(added, {
      type: 'upsertLayer',
      spec: { ...spec('new', 'result'), opacity: 0.5 },
    })
    expect(merged.layers.new.opacity).toBe(0.5)
    expect(merged.layers.new.revision).toBe(2)
    expect(merged.order).toHaveLength(3) // no duplicate
  })

  it('removeLayersByRole removes only matching roles', () => {
    const state = seeded()
    const next = sceneReducer(state, { type: 'removeLayersByRole', role: 'selection' })
    expect(next.layers['Highlight-Layer']).toBeUndefined()
    expect(next.layers.base).toBeDefined()
    expect(next.order).toEqual(['base'])
  })

  it('reorderLayers preserves unknown ids at the tail', () => {
    const state = seeded()
    const next = sceneReducer(state, { type: 'reorderLayers', order: ['Highlight-Layer'] })
    expect(next.order).toEqual(['Highlight-Layer', 'base'])
    expect(next.layers.base.order).toBe(1)
  })
})
