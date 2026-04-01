import { layerGroup } from '@/layouts/layer.js';
import { Layer } from '@/composables/useLayer.ts';
import { GeoJsonLayer } from '@deck.gl/layers';

const LAYER_ID = 'AI-Result';

/**
 * 更新地图上的 AI 结果图层
 */
export const updateChatMapLayer = (geoData) => {
  layerGroup.removeLayer(LAYER_ID);

  const resultLayer = new Layer(LAYER_ID, GeoJsonLayer, {
    opacity: 0.8,
    visible: true,
    props: {
      getFillColor: [255, 140, 66, 180],
      getLineColor: [255, 255, 255, 255],
      lineWidthMinPixels: 2,
      pointRadiusMinPixels: 8,
      pickable: true,
      name: 'AI 分析结果',
      alias: 'AI Result'
    },
    data: geoData
  });

  layerGroup.addLayer(resultLayer);

  // 置顶逻辑
  const newOrder = [...layerGroup.layers];
  const aiIndex = newOrder.findIndex(l => l.id === LAYER_ID);
  if (aiIndex > -1) {
    const [item] = newOrder.splice(aiIndex, 1);
    newOrder.unshift(item);
    layerGroup.setLayerOrder(newOrder);
  }
};

/**
 * 清除 AI 图层
 */
export const clearChatMapLayer = () => {
  layerGroup.removeLayer(LAYER_ID);
};