import { reactive, markRaw } from 'vue'
import type { LayerRole } from '@/core'

export interface LayerOptions {
  opacity?: number
  visible?: boolean
  props?: Record<string, unknown>
  data?: unknown
  /** Semantic role from the core scene model (defaults inferred from the id). */
  role?: LayerRole
}

export type LayerConstructor = new (props: Record<string, any>) => any

/** Monotonic source for per-instance revisions; a fresh layer is always new. */
let revisionSeq = 0

export class Layer {
  public id: string
  public type: LayerConstructor
  public typeName: string
  public state: Record<string, any>
  public data: unknown
  public isExpanded = false
  public role?: LayerRole
  private _revision = ++revisionSeq

  constructor(id: string, type: LayerConstructor, options: LayerOptions = {}) {
    this.id = id
    this.type = markRaw(type)
    this.typeName = (type as { layerName?: string }).layerName ?? ''
    this.state = reactive({
      opacity: options.opacity ?? 1,
      visible: options.visible ?? true,
      ...(options.props ?? {}),
    })
    this.data = options.data ? markRaw(options.data) : null
    this.role = options.role
  }

  /** Bumped on any data/visual mutation so the renderer can diff cheaply. */
  get revision(): number {
    return this._revision
  }

  /** Used by LayerGroup.updateLayerProperty / setOpacity / setVisibility. */
  set(prop: string, value: any): void {
    if (this.state[prop] === value) return
    this.state[prop] = value
    this._revision++
  }

  /** Data replacement path used by selection / result updates. */
  setData(data: unknown): void {
    this.data = data ? markRaw(data) : null
    this._revision++
  }

  get opacity(): number {
    return this.state.opacity as number
  }

  set opacity(value: number) {
    if (this.state.opacity === value) return
    this.state.opacity = value
    this._revision++
  }

  get visible(): boolean {
    return this.state.visible as boolean
  }

  set visible(value: boolean) {
    if (this.state.visible === value) return
    this.state.visible = value
    this._revision++
  }
}
