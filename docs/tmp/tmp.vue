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
                    <span class="debug-label">Payload Context</span>
                    <span class="debug-time">{{ debugInfo.timestamp }}</span>
                </div>
                <pre class="debug-content">{{ JSON.stringify(debugInfo, null, 2) }}</pre>
            </div>
        </Transition>

        <div class="chat-viewport" ref="chatRef">
            <div class="message-list">
                <div v-for="(msg, index) in messages" :key="index" :class="['msg-row', msg.role]">
                    <div class="avatar-wrapper">
                        <el-avatar :size="32"
                            :src="msg.role === 'ai' ? 'https://api.dicebear.com/7.x/bottts/svg?seed=Felix' : ''">
                            <el-icon v-if="msg.role === 'user'">
                                <User />
                            </el-icon>
                        </el-avatar>
                    </div>

                    <div class="msg-content">
                        <div class="bubble">
                            {{ msg.content }}
                        </div>
                    </div>
                </div>
                <div v-if="isTyping" class="msg-row ai">
                    <div class="avatar-wrapper">
                        <el-avatar :size="32" src="https://api.dicebear.com/7.x/bottts/svg?seed=Felix" />
                    </div>
                    <div class="typing-indicator">
                        <span></span><span></span><span></span>
                    </div>
                </div>
            </div>
        </div>

        <div class="input-fixed-bottom">
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

            <div class="input-card" :class="{ 'has-tip': selectedRegion }">
                <el-input v-model="inputMsg" type="textarea" :rows="2" placeholder="Ask a question..." resize="none"
                    @keydown.enter.exact.prevent="handleSend" />
                <div class="input-actions">
                    <span class="input-tip"><b>Enter</b> send / <b>Shift+Enter</b> wrap</span>
                    <el-button type="primary" size="default" :loading="isTyping" @click="handleSend"
                        :disabled="!inputMsg.trim()">
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
import { ref, nextTick, computed } from 'vue';
import { User, Promotion, Monitor, LocationInformation } from '@element-plus/icons-vue';
import { useMapStore } from '@/stores/mapStore';
import { layerGroup } from '@/layouts/layer.js';
import { Layer } from '@/composables/useLayer.ts';
import { GeoJsonLayer } from '@deck.gl/layers';

const mapStore = useMapStore();
const emit = defineEmits(['refresh-map']);

const inputMsg = ref('');
const isTyping = ref(false);
const chatRef = ref(null);
const showDebug = ref(false);
const debugInfo = ref({ timestamp: 'Waiting...' });
const chatRound = ref(0);

const selectedRegion = computed(() => mapStore.selectedRegion);
const messages = ref([
    { role: 'ai', content: 'Map system initialized. I can analyze layers and specific objects. How can I help?' }
]);

const scrollToBottom = async () => {
    await nextTick();
    if (chatRef.value) {
        chatRef.value.scrollTo({ top: chatRef.value.scrollHeight, behavior: 'smooth' });
    }
};

const clearSelection = () => mapStore.updateSelectedRegion(null);

const handleSend = async () => {
    const content = inputMsg.value.trim();
    if (!content || isTyping.value) return;

    const context = selectedRegion.value ? {
        id: selectedRegion.value.id,
        props: selectedRegion.value.properties || {}
    } : null;

    debugInfo.value = {
        query: content,
        context: context,
        timestamp: new Date().toLocaleTimeString()
    };

    inputMsg.value = '';
    chatRound.value++;
    messages.value.push({ role: 'user', content });
    scrollToBottom();
    isTyping.value = true;

    setTimeout(() => {
        let responseText = "I've analyzed the current map view.";
        if (context) {
            responseText = `I see you've selected "${context.props.name || context.id}". I'm calculating the spatial relationships...`;
        }

        if (chatRound.value === 2) {
            responseText = "Analysis complete. I've added a new high-priority layer with red markers to the map.";
            const mockResult = {
                type: "FeatureCollection",
                features: [
                    {
                        type: "Feature",
                        geometry: { type: "Point", coordinates: [114.15470, 22.27842] },
                        properties: { id: "AI-001", name: "Cluster A", info: "Derived via AI" }
                    },
                    {
                        type: "Feature",
                        geometry: { type: "Point", coordinates: [114.15500, 22.27859] },
                        properties: { id: "AI-002", name: "Cluster B", info: "Derived via AI" }
                    }
                ]
            };

            const resultLayer = new Layer('AI-Result', GeoJsonLayer, {
                opacity: 1,
                visible: true,
                props: {
                    pointRadiusMinPixels: 8,
                    getFillColor: [255, 59, 48],
                    getLineColor: [255, 255, 255],
                    lineWidthMinPixels: 2,
                    pickable: true
                },
                data: mockResult
            });

            layerGroup.layers.unshift(resultLayer);
            emit('refresh-map');
        }

        messages.value.push({ role: 'ai', content: responseText });
        isTyping.value = false;
        scrollToBottom();
    }, 1500);
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

/* Header Styling */
.chat-header {
    padding: 0 16px;
    height: 56px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid var(--el-border-color-lighter);
    background-color: var(--el-bg-color-overlay);
}

.title-main {
    font-weight: 600;
    font-size: 15px;
    margin-right: 8px;
}

.btn-text {
    margin-left: 4px;
    font-size: 12px;
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

.debug-label {
    color: var(--el-color-warning);
    font-weight: bold;
}

.debug-content {
    color: #00ff00;
    margin: 0;
    white-space: pre-wrap;
    line-height: 1.4;
}

/* Viewport & Messages */
.chat-viewport {
    flex: 1;
    overflow-y: auto;
    padding: 20px 16px;
}

.message-list {
    display: flex;
    flex-direction: column;
    gap: 20px;
}

.msg-row {
    display: flex;
    gap: 12px;
    max-width: 88%;
}

.msg-row.user {
    align-self: flex-end;
    flex-direction: row-reverse;
}

/* 关键修复：防止头像挤压 */
.avatar-wrapper {
    flex-shrink: 0;
    display: flex;
    align-items: flex-end;
}

.bubble {
    padding: 12px 16px;
    border-radius: 16px;
    font-size: 14px;
    line-height: 1.5;
    position: relative;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
}

.ai .bubble {
    background: var(--el-fill-color-light);
    color: var(--el-text-color-primary);
    border-bottom-left-radius: 4px;
}

.user .bubble {
    background: var(--el-color-primary);
    color: white;
    border-bottom-right-radius: 4px;
}

/* Typing Indicator */
.typing-indicator {
    display: flex;
    gap: 4px;
    padding: 12px 16px;
    background: var(--el-fill-color-lighter);
    border-radius: 16px;
    width: fit-content;
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

/* Input Area Area */
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

.tip-body {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 12px;
    overflow: hidden;
}

.tip-text {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
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
    border-top: none;
}

.input-card:focus-within {
    border-color: var(--el-color-primary);
    box-shadow: 0 0 0 1px var(--el-color-primary-light-7);
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
</style>