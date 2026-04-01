import { ref, reactive, computed } from 'vue';
import { useMapStore } from '@/stores/mapStore';
import { layerGroup } from '@/layouts/layer.js';
import { Layer } from '@/composables/useLayer.ts';
import { GeoJsonLayer } from '@deck.gl/layers';

export function useChatLogic(emit) {
  const mapStore = useMapStore();
  
  // 业务状态
  const isTyping = ref(false);
  const currentStatus = ref('');
  const debugInfo = ref({ timestamp: 'Waiting...' });
  const rawHistory = ref([]);
  const selectedRegion = computed(() => mapStore.selectedRegion);

  const clearSelection = () => mapStore.updateSelectedRegion(null);

  /**
   * 地图图层更新逻辑 (从 UI 组件中剥离)
   */
  const updateMapLayer = (geoData) => {
    const LAYER_ID = 'AI-Result';
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

    const newOrder = [...layerGroup.layers];
    const aiIndex = newOrder.findIndex(l => l.id === LAYER_ID);
    if (aiIndex > -1) {
      const [item] = newOrder.splice(aiIndex, 1);
      newOrder.unshift(item);
      layerGroup.setLayerOrder(newOrder);
    }
    emit('refresh-map');
  };

  /**
   * 核心流式请求逻辑
   */
  const sendMessage = async (query, onMessageUpdate) => {
    if (!query || isTyping.value) return;

    // 更新 Debug 信息
    debugInfo.value = {
      query,
      context: selectedRegion.value,
      history_len: rawHistory.value.length,
      timestamp: new Date().toLocaleTimeString()
    };

    isTyping.value = true;
    currentStatus.value = 'Connecting to GeoAI Service...';

    // 创建响应式的 AI 消息引用
    const aiMsg = { role: 'ai', content: '' };
    
    try {
      const response = await fetch("http://localhost:8000/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query,
          history: rawHistory.value,
          context_features: selectedRegion.value
        }),
      });

      if (!response.ok) throw new Error(`HTTP Error ${response.status}`);

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split("\n");

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const jsonStr = line.replace("data: ", "").trim();
          if (!jsonStr) continue;

          try {
            const { type, data } = JSON.parse(jsonStr);
            if (type === "status") {
              currentStatus.value = data;
            } else if (type === "final_result") {
              aiMsg.content = data.report.final_report || data.report.guidance;
              rawHistory.value = JSON.parse(data.new_history);
              if (data.geojson) updateMapLayer(data.geojson);
              // 回调通知 UI 最终内容
              onMessageUpdate(aiMsg.content);
            }
          } catch (e) { console.error('Parse Error', e); }
        }
      }
    } catch (error) {
      aiMsg.content = `❌ Error: ${error.message}`;
      onMessageUpdate(aiMsg.content);
    } finally {
      isTyping.value = false;
      currentStatus.value = '';
    }
  };

  return {
    isTyping,
    currentStatus,
    debugInfo,
    selectedRegion,
    clearSelection,
    sendMessage
  };
}