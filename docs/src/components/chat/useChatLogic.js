import { ref, computed } from 'vue';
import { useMapStore } from '@/stores/mapStore';
import { geoAI } from '@/services/geoApi';
import { updateChatMapLayer } from './chatMapUtils';

export function useChatLogic(emit) {
  const mapStore = useMapStore();
  
  // 1. 响应式状态
  const isTyping = ref(false);
  const currentStatus = ref('');
  const rawHistory = ref([]);
  const debugInfo = ref({ timestamp: 'Waiting...' });
  const selectedRegion = computed(() => mapStore.selectedRegion);

  // 2. 核心逻辑
  const sendMessage = async (query, onMessageUpdate) => {
    if (!query || isTyping.value) return;

    // 预设状态
    isTyping.value = true;
    currentStatus.value = 'Preparing...';
    debugInfo.value = {
      query,
      history_len: rawHistory.value.length,
      timestamp: new Date().toLocaleTimeString()
    };

    await geoAI.chat(
      { 
        query, 
        history: rawHistory.value, 
      },
      {
        onStatus: (status) => {
          currentStatus.value = status;
        },
        onGeoJson: (geoData) => {
          updateChatMapLayer(geoData);
          emit('refresh-map');
        },
        onFinal: ({ report, history }) => {
          rawHistory.value = history;
          const content = report.final_report || report.guidance;
          onMessageUpdate(content);
        },
        onError: (err) => {
          onMessageUpdate(`❌ Error: ${err.message}`);
        }
      }
    );

    isTyping.value = false;
    currentStatus.value = '';
  };

  return {
    isTyping,
    currentStatus,
    debugInfo,
    selectedRegion,
    sendMessage,
    clearSelection: () => mapStore.updateSelectedRegion(null)
  };
}