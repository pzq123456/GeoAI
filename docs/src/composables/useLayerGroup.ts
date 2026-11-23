import { reactive } from 'vue'
import { Layer } from './useLayer'
import type { LayerRole } from '@/core'

export { Layer } from './useLayer'

export interface LayerItem {
  id: string
  type: new (props: Record<string, any>) => any
  visible: boolean
  opacity: number
  state: Record<string, any>
  data: any
  isExpanded: boolean
  /** Monotonic data/style counter used by the map renderer for diffing. */
  revision: number
  role?: LayerRole
  set: (prop: string, value: any) => void
  setData: (data: unknown) => void
}

export class LayerGroup {
  layers: LayerItem[]

  constructor(layers: LayerItem[] = []) {
    this.layers = reactive(layers) as LayerItem[]
  }

  addLayer(layer: LayerItem): void {
    this.layers.push(layer)
  }

  removeLayer(layerId: string): void {
    const index = this.layers.findIndex((l) => l.id === layerId)
    if (index !== -1) this.layers.splice(index, 1)
  }

  updateLayerProperty(layerId: string, prop: string, value: any): void {
    const layer = this.layers.find((l) => l.id === layerId)
    if (layer && typeof layer.set === 'function') layer.set(prop, value)
  }

  setOpacity(layerId: string, opacity: number): void {
    this.updateLayerProperty(layerId, 'opacity', opacity)
  }

  setVisibility(layerId: string, visible: boolean): void {
    this.updateLayerProperty(layerId, 'visible', visible)
  }

  setLayerOrder(newOrder: LayerItem[]): void {
    this.layers.length = 0
    this.layers.push(...newOrder)
  }

  /**
   * UI 列表是「上到下 = 图层的上到下」；deck.gl 的数组顺序是「先画 = 底层」，
   * 所以这里必须 reverse，否则高亮层会被基础层盖住。
   *
   * 交互不要手工挑 layer：deck.gl 自带 picking 的层级判定（命中多个时取最上层），
   * 把 pickable 交给每个图层自己的 state 决定即可。
   * 旧实现 `pickable = index === 0` 在 reverse 之后指向的是最底层，是个 bug。
   */
  getLayers(): any[] {
    // Keep ALL layers in the array, including hidden ones. Visibility is a
    // deck.gl prop (already inside `layer.state`), not an array-membership
    // decision. Removing hidden layers from the array makes deck.gl finalize
    // their instances; reusing those finalized instances later crashes with
    // "finalized layer cannot be reused" and takes down the whole overlay.
    return [...this.layers].reverse().map((layer) => {
      const LayerType = layer.type
      return new LayerType({
        id: layer.id,
        pickable: true,
        ...layer.state,
        // Top-level data wins; layers created with `props.data` alone fall back
        // to their reactive state (this is how the highlight layer starts empty).
        data: layer.data ?? layer.state.data,
      })
    })
  }
}
