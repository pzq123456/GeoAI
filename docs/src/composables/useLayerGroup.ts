import { reactive } from 'vue';

export { Layer } from './useLayer.ts';

export interface LayerItem {
  id: string;
  type: new (props: any) => any;
  visible: boolean;
  state: Record<string, any>;
  data: any;
  set: (prop: string, value: any) => void;
  [key: string]: any;
}

export class LayerGroup {
  layers: LayerItem[];

  constructor(layers: LayerItem[] = []) {
    this.layers = reactive(layers) as LayerItem[];
  }

  // 添加新图层
  addLayer(layer: LayerItem) {
    this.layers.push(layer);
  }

  // 移除图层
  removeLayer(layerId: string) {
    const index = this.layers.findIndex(l => l.id === layerId);
    if (index !== -1) {
      this.layers.splice(index, 1);
    }
  }

  // 通用属性更新方法
  updateLayerProperty(layerId: string, prop: string, value: any) {
    const layer = this.layers.find(l => l.id === layerId);
    if (layer && typeof layer.set === 'function') {
      layer.set(prop, value);
    }
  }

  // 更新图层的不透明度（保持兼容性）
  setOpacity(layerId: string, opacity: number) {
    this.updateLayerProperty(layerId, 'opacity', opacity);
  }

  // 更新图层的可见性（保持兼容性）
  setVisibility(layerId: string, visible: boolean) {
    this.updateLayerProperty(layerId, 'visible', visible);
  }

  // 设置图层顺序（支持拖拽）
  setLayerOrder(newOrder: LayerItem[]) {
    this.layers.length = 0;
    this.layers.push(...newOrder);
  }

  // 根据图层类型和属性生成 DeckGL 图层
  getLayers(): any[] {
    const visibleLayers = this.layers.filter(layer => layer.visible).reverse();

    return visibleLayers.map((layer, index) => {
      const LayerType = layer.type;
      // 只有最上层图层（数组的第一个元素）也就是倒数第一个元素的 pickable 为 true
      const pickable = index === visibleLayers.length - 1;

      // 收集所有状态属性
      const layerProps = {
        id: `${layer.id}-${Date.now()}`,
        pickable,
        ...layer.state,
        data: layer.data
      };

      return new LayerType(layerProps);
    });
  }
}