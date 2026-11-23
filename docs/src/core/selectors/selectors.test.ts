import { describe, expect, it } from 'vitest'
import {
  buildContext,
  createEmptyScene,
  resultToLayer,
  sceneReducer,
  type GeoJsonFeature,
  type LayerSpec,
} from '@/core'

const feature: GeoJsonFeature = {
  type: 'Feature',
  id: 7,
  geometry: { type: 'Point', coordinates: [114, 22] },
  properties: { name: 'Tree 7' },
}

const spec = (id: string, visible = true): LayerSpec => ({
  id,
  role: 'base',
  source: { kind: 'geojson', features: [] },
  style: { color: [1, 2, 3, 255] },
  visible,
  opacity: 1,
  order: 0,
  revision: 1,
})

describe('buildContext', () => {
  it('projects selection, viewport and visible layer ids', () => {
    let scene = createEmptyScene()
    scene = sceneReducer(scene, {
      type: 'replaceLayers',
      specs: [spec('visible'), spec('hidden', false)],
    })
    scene = sceneReducer(scene, { type: 'selectFeature', feature })
    scene = sceneReducer(scene, {
      type: 'setViewport',
      viewport: { center: [1, 2], zoom: 12, bearing: 0, pitch: 0 },
    })

    const ctx = buildContext(scene)
    expect(ctx.selectedFeature).toEqual({
      id: 7,
      properties: { name: 'Tree 7' },
      geometryType: 'Point',
    })
    expect(ctx.viewport).toEqual({ center: [1, 2], zoom: 12 })
    expect(ctx.layers).toEqual(['visible'])
  })

  it('returns null selectedFeature for an empty scene', () => {
    expect(buildContext(createEmptyScene()).selectedFeature).toBeNull()
  })
})

describe('resultToLayer', () => {
  it('returns a result-role layer for a non-empty FeatureCollection', () => {
    const layer = resultToLayer({
      geojson: { type: 'FeatureCollection', features: [feature] },
    })
    expect(layer).not.toBeNull()
    expect(layer).toMatchObject({
      id: 'AI-Result',
      role: 'result',
      visible: true,
      opacity: 0.8,
      revision: 1,
    })
    expect(layer?.source).toEqual({
      kind: 'geojson-collection',
      collection: { type: 'FeatureCollection', features: [feature] },
    })
  })

  it('returns null when there is no geojson or no features', () => {
    expect(resultToLayer({})).toBeNull()
    expect(resultToLayer({ geojson: { type: 'FeatureCollection', features: [] } })).toBeNull()
  })
})
