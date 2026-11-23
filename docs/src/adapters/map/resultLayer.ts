/** Materialise a core result-role `LayerSpec` as the legacy deck.gl Layer. */

import { GeoJsonLayer } from '@deck.gl/layers'
import { Layer, type LayerItem } from '@/composables/useLayerGroup'
import type { LayerConstructor } from '@/composables/useLayer'
import { sourceFeatures, type LayerSpec } from '@/core'
import { resultDeckProps } from './deckStyle'

export function createResultLayer(spec: LayerSpec): LayerItem {
  return new Layer(spec.id, GeoJsonLayer as unknown as LayerConstructor, {
    role: 'result',
    opacity: spec.opacity,
    visible: spec.visible,
    props: {
      ...resultDeckProps(),
      name: 'AI 分析结果',
      alias: 'AI Result',
    },
    data: sourceFeatures(spec.source),
  })
}
