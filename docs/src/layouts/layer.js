import { Layer, LayerGroup } from '@/composables/useLayerGroup.ts'
import { GeoJsonLayer } from '@deck.gl/layers'
// import { data as park_data } from '@/loaders/park.data.js';
// import { data as poi_data } from '@/loaders/poi.data.js';
import { data as school_data } from '@/loaders/schools.data.js';

import { useMapStore } from '@/stores/mapStore';

const mapStore = useMapStore();

// const parkLayer = new Layer('Park-Layer', GeoJsonLayer, {
//   opacity: 0.5,
//   visible: true,
//   props: {
//     lineWidthMinPixels: 1,
//     getLineColor: [128, 128, 128],
//     pickable: true,
//     getFillColor: [0, 128, 255, 100],
//     onClick: (info, event) => {
//       if (!info.object) return;
//       const regionData = info.object;
//       mapStore.updateSelectedRegion(regionData);
//     }
//   },
//   data: park_data.features
// });

// const poiLayer = new Layer('Poi-Layer', GeoJsonLayer, {
//   opacity: 0.5,
//   visible: true,
//   props: {
//     lineWidthMinPixels: 1,
//     getLineColor: [128, 128, 128],
//     pickable: true,
//     onClick: (info, event) => {
//       if (!info.object) return;
//       const regionData = info.object;
//       mapStore.updateSelectedRegion(regionData);
//     }
//   },
//   data: poi_data.features
// });

const schoolLayer = new Layer('School-Layer', GeoJsonLayer, {
  opacity: 0.5,
  visible: true,
  props: {
    lineWidthMinPixels: 10,
    getLineColor: [128, 128, 128],
    pickable: true,
    onClick: (info) => {
      if (!info.object) return;
      const regionData = info.object;
      mapStore.updateSelectedRegion(regionData);
    }
  },
  data: school_data.features
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
  // parkLayer,
  // poiLayer,
  schoolLayer
]);

export { layerGroup };