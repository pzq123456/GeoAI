import { Layer, LayerGroup } from '@/composables/useLayerGroup.ts'
import { GeoJsonLayer } from '@deck.gl/layers'
import { data as tree_data } from '@/loaders/tree.data.js';


import { useMapStore } from '@/stores/mapStore';

const mapStore = useMapStore();

const treeLayer = new Layer('tree-Layer', GeoJsonLayer, {
  opacity: 0.5,
  visible: true,
  props: {
    lineWidthMinPixels: 2,
    getLineColor: [128, 128, 128],
    getFillColor: [0, 25, 18, 10],
    pickable: true,
    onClick: (info) => {
      if (!info.object) return;
      const regionData = info.object;
      mapStore.updateSelectedRegion(regionData);
    }
  },
  data: tree_data.features
});

// 高亮图层（仅用于持久化高亮）
const highlightLayer = new Layer('Highlight-Layer', GeoJsonLayer, {
  opacity: 0.8,
  visible: true,
  props: {
    data: [],
    lineWidthMinPixels: 12,
    getLineColor: [255, 12, 0, 255],
    getFillColor: [255, 23, 0, 100],
    pickable: false // 完全禁用交互
  }
});

// 图层组合
const layerGroup = new LayerGroup([
  highlightLayer,
  treeLayer
]);

export { layerGroup };