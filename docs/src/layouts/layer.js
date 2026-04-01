import { Layer, LayerGroup } from '@/composables/useLayerGroup.ts'
import { GeoJsonLayer } from '@deck.gl/layers'
// import { data } from '@/loaders/usa2014_2024.data.js'
import { data as park_data } from '@/loaders/park.data.js';
import { data as poi_data } from '@/loaders/poi.data.js';

// import { useColorBandStore } from '@/stores/colorBandStore'
// import { createNormalizer } from '@/utils/normalizer';
// import { hexToRgbaArray } from '@/utils/color';
import { useMapStore } from '@/stores/mapStore';

const mapStore = useMapStore();
// const store = useColorBandStore();

// const column = "Year2014";
// const normalizeYearData = createNormalizer(data.features, column, { mode: 'log', boundaryEpsilon: 1e-4 });

// function getDataValue(d) {
//   const value = d.properties[column];
//   const normalizedValue = normalizeYearData(value);
//   return normalizedValue;
// }

// function getFillColor(d) {
//   const normalizedValue = getDataValue(d);
//   const hexColor = store.currentColorBand(normalizedValue);
//   return hexToRgbaArray(hexColor);
// }

// console.log(park_data);
// USA 基础图层
const parkLayer = new Layer('Park-Layer', GeoJsonLayer, {
  opacity: 0.5,
  visible: true,
  props: {
    lineWidthMinPixels: 1,
    getLineColor: [128, 128, 128],
    pickable: true,
    getFillColor: [0, 128, 255, 100],
    onClick: (info, event) => {
      if (!info.object) return;
      const regionData = info.object;
      mapStore.updateSelectedRegion(regionData);
    }
  },
  data: park_data.features
});

const poiLayer = new Layer('Poi-Layer', GeoJsonLayer, {
  opacity: 0.5,
  visible: true,
  props: {
    lineWidthMinPixels: 1,
    getLineColor: [128, 128, 128],
    pickable: true,
    onClick: (info, event) => {
      if (!info.object) return;
      const regionData = info.object;
      mapStore.updateSelectedRegion(regionData);
    }
  },
  data: poi_data.features
});

// 高亮图层（仅用于持久化高亮）
const highlightLayer = new Layer('Highlight-Layer', GeoJsonLayer, {
  opacity: 0.8,
  visible: true,
  props: {
    data: [],
    lineWidthMinPixels: 2,
    getLineColor: [255, 12, 0, 255],
    getFillColor: [255, 23, 0, 100],
    pickable: false // 完全禁用交互
  }
});

// 图层组合
const layerGroup = new LayerGroup([
  highlightLayer,
  parkLayer,
  poiLayer
]);

export { layerGroup };