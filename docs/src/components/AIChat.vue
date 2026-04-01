<template>
  <div class="chat-container-fixed">
    <div class="chat-header">
      <div class="header-left">
        <span class="title-main">AI Map Assistant</span>
        <el-tag size="small" type="success" effect="plain" round>Active</el-tag>
      </div>
      <div class="header-right">
        <el-button :type="showDebug ? 'warning' : 'info'" size="small" plain @click="showDebug = !showDebug">
          <el-icon>
            <Monitor />
          </el-icon>
          <span class="btn-text">{{ showDebug ? 'Hide Logs' : 'Debug' }}</span>
        </el-button>
      </div>
    </div>

    <Transition name="el-zoom-in-top">
      <div v-if="showDebug" class="debug-panel">
        <div class="debug-header">
          <span>Payload Context</span>
          <span>{{ debugInfo.timestamp }}</span>
        </div>
        <pre class="debug-content">{{ JSON.stringify(debugInfo, null, 2) }}</pre>
      </div>
    </Transition>

    <div class="chat-viewport" ref="chatRef">
      <div class="message-list">
        <div v-for="(msg, index) in messages" :key="index" :class="['msg-row', msg.role]">
          <div class="avatar-wrapper">
            <el-avatar :size="32" :src="msg.role === 'ai' ? 'https://api.dicebear.com/7.x/bottts/svg?seed=Felix' : ''">
              <el-icon v-if="msg.role === 'user'">
                <User />
              </el-icon>
            </el-avatar>
          </div>
          <div class="msg-content">
            <div class="bubble">
              <template v-if="msg.role === 'ai'">
                <MarkdownRender v-if="msg.content" :content="msg.content" custom-id="map-ai-renderer" />
                <div v-else class="typing-placeholder">Generating analysis...</div>
              </template>
              <template v-else>
                {{ msg.content }}
              </template>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="input-fixed-bottom">
      <Transition name="el-slide-in-bottom">
        <div v-if="isTyping" class="status-bar">
          <div class="status-content">
            <div class="mini-typing">
              <span></span><span></span><span></span>
            </div>
            <span class="status-text">{{ currentStatus || 'AI is thinking...' }}</span>
          </div>
        </div>
      </Transition>

      <Transition name="el-slide-in-bottom">
        <div v-if="selectedRegion" class="selection-tip">
          <div class="tip-body">
            <el-icon color="var(--el-color-primary)">
              <LocationInformation />
            </el-icon>
            <span class="tip-text">
              Context: <b>{{ selectedRegion.properties?.name || selectedRegion.id }}</b>
            </span>
          </div>
          <el-button link type="primary" size="small" @click="clearSelection">Clear</el-button>
        </div>
      </Transition>

      <div class="input-card" :class="{ 'has-tip': selectedRegion || isTyping }">
        <el-input v-model="inputMsg" type="textarea" :rows="2" placeholder="Ask about the map..." resize="none"
          @keydown.enter.exact.prevent="handleSend" />
        <div class="input-actions">
          <span class="input-tip"><b>Enter</b> send / <b>Shift+Enter</b> wrap</span>
          <el-button type="primary" :loading="isTyping" @click="handleSend" :disabled="!inputMsg.trim()">
            <el-icon>
              <Promotion />
            </el-icon>
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, computed, reactive } from 'vue';
import { User, Promotion, Monitor, LocationInformation } from '@element-plus/icons-vue';
import { useMapStore } from '@/stores/mapStore';
import { layerGroup } from '@/layouts/layer.js';
import { Layer } from '@/composables/useLayer.ts';
import { GeoJsonLayer } from '@deck.gl/layers';
import MarkdownRender from 'markstream-vue';
import 'markstream-vue/index.css';

const mapStore = useMapStore();
const emit = defineEmits(['refresh-map']);

const inputMsg = ref('');
const isTyping = ref(false);
const currentStatus = ref('');     // 专门承载“状态上报”，不干扰对话内容
const chatRef = ref(null);
const showDebug = ref(false);
const debugInfo = ref({ timestamp: 'Waiting...' });
const rawHistory = ref([]);

const messages = ref([
  { role: 'ai', content: 'Map system initialized. Select an object or ask a question.' }
]);

const selectedRegion = computed(() => mapStore.selectedRegion);

const scrollToBottom = async () => {
  await nextTick();
  if (chatRef.value) {
    chatRef.value.scrollTo({ top: chatRef.value.scrollHeight, behavior: 'smooth' });
  }
};

const clearSelection = () => mapStore.updateSelectedRegion(null);

/**
 * 核心请求逻辑
 */
const handleSend = async () => {
  const query = inputMsg.value.trim();
  if (!query || isTyping.value) return;

  console.log('--- [ATOM] START_SEND ---', { query, hasContext: !!selectedRegion.value });

  debugInfo.value = {
    query,
    context: selectedRegion.value,
    history_len: rawHistory.value.length,
    timestamp: new Date().toLocaleTimeString()
  };

  messages.value.push({ role: 'user', content: query });
  inputMsg.value = '';
  await scrollToBottom();

  isTyping.value = true;
  currentStatus.value = 'Connecting to GeoAI Service...';

  // 创建一个空的 AI 响应对象，此时 content 为空
  const aiMsg = reactive({ role: 'ai', content: '' });
  messages.value.push(aiMsg);

  try {
    const response = await fetch("http://localhost:8000/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query: query,
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
            console.log('--- [ATOM] STATUS_UPDATE ---', data);
            currentStatus.value = data; // 更新底部的状态条，不更新气泡
          }

          else if (type === "final_result") {
            console.log('--- [ATOM] FINAL_RESULT_RECEIVED ---');

            // 1. 填充对话气泡 (执行原子动作 A)
            aiMsg.content = data.report.final_report || data.report.guidance;

            // 2. 更新记忆 (执行原子动作 B)
            rawHistory.value = JSON.parse(data.new_history);
            console.log('--- [ATOM] HISTORY_UPDATED ---', rawHistory.value.length);

            // 3. 地图渲染 (执行原子动作 C)
            if (data.geojson) {
              console.log('--- [ATOM] GEOJSON_RENDER ---', data.geojson.features?.length);
              updateMapLayer(data.geojson);
            }
          }
        } catch (e) {
          console.error('--- [ATOM] PARSE_ERROR ---', e);
        }
      }
    }
  } catch (error) {
    console.error('--- [ATOM] FATAL_ERROR ---', error);
    aiMsg.content = `❌ Error: ${error.message}`;
  } finally {
    console.log('--- [ATOM] SESSION_FINISHED ---');
    isTyping.value = false;
    currentStatus.value = '';
    await scrollToBottom();
  }
};

const updateMapLayer = (geoData) => {
  const LAYER_ID = 'AI-Result';

  // 1. 使用系统标准方法移除旧图层，这会触发系统的响应式更新
  layerGroup.removeLayer(LAYER_ID);

  // 2. 构造符合规范的 Layer 实例
  // 颜色改为半透明科技蓝，解决遮挡和红色高亮冲突
  const resultLayer = new Layer(LAYER_ID, GeoJsonLayer, {
    opacity: 0.8,
    visible: true,
    props: {
      getFillColor: [255, 140, 66, 180],   // 暖橙，半透明
      getLineColor: [255, 255, 255, 255],  // 白色描边
      lineWidthMinPixels: 2,
      pointRadiusMinPixels: 8,
      pickable: true,
      // 必须：添加 UI 显示所需的元数据，否则面板无法展示名字
      name: 'AI 分析结果',
      alias: 'AI Result'
    },
    data: geoData
  });

  // 3. 【核心修复】调用 LayerGroup 提供的标准方法
  // addLayer 会自动推入 reactive 数组，并触发所有订阅该数组的 UI 组件刷新
  layerGroup.addLayer(resultLayer);

  // 4. 【排序修复】如果你希望它在最上层且能参与拖拽
  // 我们可以通过 setLayerOrder 将其置顶，同时保持其作为“系统成员”的身份
  const newOrder = [...layerGroup.layers];
  const aiIndex = newOrder.findIndex(l => l.id === LAYER_ID);
  if (aiIndex > -1) {
    const [item] = newOrder.splice(aiIndex, 1);
    newOrder.unshift(item); // 放到数组首位
    layerGroup.setLayerOrder(newOrder); // 触发系统的排序逻辑
  }

  // 5. 通知地图重绘
  emit('refresh-map');
};
</script>

<style scoped>
.chat-container-fixed {
  height: 100%;
  display: flex;
  flex-direction: column;
  background-color: var(--el-bg-color);
  color: var(--el-text-color-primary);
}

/* Header */
.chat-header {
  padding: 0 16px;
  height: 56px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--el-border-color-lighter);
  background-color: var(--el-bg-color-overlay);
  z-index: 10;
}

.title-main {
  font-weight: 600;
  font-size: 15px;
  margin-right: 8px;
}

/* Debug Panel */
.debug-panel {
  background: #1a1a1a;
  padding: 12px;
  font-family: 'Fira Code', monospace;
  font-size: 11px;
  border-bottom: 2px solid var(--el-color-warning);
}

.debug-header {
  display: flex;
  justify-content: space-between;
  color: #888;
  margin-bottom: 6px;
}

.debug-content {
  color: #00ff00;
  margin: 0;
  white-space: pre-wrap;
  line-height: 1.4;
}

/* Viewport */
.chat-viewport {
  flex: 1;
  overflow-y: auto;
  padding: 20px 16px;
}

.message-list {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.msg-row {
  display: flex;
  gap: 12px;
  max-width: 92%;
}

.msg-row.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.avatar-wrapper {
  flex-shrink: 0;
  display: flex;
  align-items: flex-start;
}

.bubble {
  padding: 8px 14px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.6;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.ai .bubble {
  background: var(--el-fill-color-light);
  color: var(--el-text-color-primary);
  border-top-left-radius: 2px;
  width: 100%;
  /* 让 Markdown 容器有足够空间 */
}

.user .bubble {
  background: var(--el-color-primary);
  color: white;
  border-top-right-radius: 2px;
}

/* Markdown Specific Overrides */
:deep(.markstream-vue) {
  background: transparent !important;
  font-family: inherit;
}

:deep(.markstream-vue p) {
  margin: 4px 0;
}

:deep(.markstream-vue h3) {
  margin: 0 0 8px 0;
  font-size: 16px;
  color: var(--el-color-primary);
}

:deep(.markstream-vue h4) {
  margin: 12px 0 4px 0;
  font-size: 14px;
}

:deep(.markstream-vue code) {
  background: rgba(0, 0, 0, 0.06);
  padding: 2px 4px;
  border-radius: 4px;
  font-size: 0.9em;
}

:deep(.markstream-vue pre) {
  background: #282c34;
  color: #abb2bf;
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 8px 0;
}

/* Typing Animation */
.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 12px 16px;
  background: var(--el-fill-color-lighter);
  border-radius: 12px;
}

.typing-indicator span {
  width: 6px;
  height: 6px;
  background: #999;
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out both;
}

.typing-indicator span:nth-child(1) {
  animation-delay: -0.32s;
}

.typing-indicator span:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes bounce {

  0%,
  80%,
  100% {
    transform: scale(0);
  }

  40% {
    transform: scale(1);
  }
}

/* Input Fixed Area */
.input-fixed-bottom {
  padding: 16px;
  background: var(--el-bg-color-overlay);
  border-top: 1px solid var(--el-border-color-lighter);
}

.selection-tip {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: var(--el-color-primary-light-9);
  border: 1px solid var(--el-color-primary-light-8);
  border-bottom: none;
  border-radius: 8px 8px 0 0;
}

.tip-text {
  font-size: 12px;
  color: var(--el-color-primary);
}

.input-card {
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  padding: 10px;
  transition: all 0.3s;
  background: var(--el-bg-color);
}

.input-card.has-tip {
  border-top-left-radius: 0;
  border-top-right-radius: 0;
}

.input-card:focus-within {
  border-color: var(--el-color-primary);
}

:deep(.el-textarea__inner) {
  border: none;
  box-shadow: none;
  padding: 5px;
  background: transparent;
}

.input-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid var(--el-border-color-extra-light);
}

.input-tip {
  font-size: 11px;
  color: var(--el-text-color-placeholder);
}

.status-bar {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  background: var(--el-color-info-light-9);
  border: 1px solid var(--el-border-color-lighter);
  border-bottom: none;
  border-radius: 8px 8px 0 0;
}

.status-content {
  display: flex;
  align-items: center;
  gap: 10px;
}

.status-text {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  font-style: italic;
}

/* 迷你打字机动画 */
.mini-typing {
  display: flex;
  gap: 3px;
}

.mini-typing span {
  width: 4px;
  height: 4px;
  background: var(--el-color-primary);
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out both;
}

.mini-typing span:nth-child(1) {
  animation-delay: -0.32s;
}

.mini-typing span:nth-child(2) {
  animation-delay: -0.16s;
}

.typing-placeholder {
  color: var(--el-text-color-placeholder);
  font-size: 13px;
  display: flex;
  align-items: center;
}

:deep(.markstream-vue blockquote) {
  border-left: 4px solid var(--el-color-primary-light-5);
  margin: 0;
  padding-left: 12px;
  color: var(--el-text-color-secondary);
  background: var(--el-fill-color-lighter);
  border-radius: 4px;
}
</style>