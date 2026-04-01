<template>
  <div class="chat-container-fixed">
    <div class="chat-header">
      <div class="header-left">
        <span class="title-main">AI Map Assistant</span>
        <el-tag size="small" type="success" effect="plain" round>Active</el-tag>
      </div>
      <div class="header-right">
        <el-button :type="showDebug ? 'warning' : 'info'" size="small" plain @click="showDebug = !showDebug">
          <el-icon><Monitor /></el-icon>
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
              <el-icon v-if="msg.role === 'user'"><User /></el-icon>
            </el-avatar>
          </div>
          <div class="msg-content">
            <div class="bubble">
              <template v-if="msg.role === 'ai'">
                <MarkdownRender v-if="msg.content" :content="msg.content" custom-id="map-ai-renderer" />
                <div v-else class="typing-placeholder">Generating analysis...</div>
              </template>
              <template v-else>{{ msg.content }}</template>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="input-fixed-bottom">
      <Transition name="el-slide-in-bottom">
        <div v-if="isTyping" class="status-bar">
          <div class="status-content">
            <div class="mini-typing"><span></span><span></span><span></span></div>
            <span class="status-text">{{ currentStatus || 'AI is thinking...' }}</span>
          </div>
        </div>
      </Transition>

      <Transition name="el-slide-in-bottom">
        <div v-if="selectedRegion" class="selection-tip">
          <div class="tip-body">
            <el-icon color="var(--el-color-primary)"><LocationInformation /></el-icon>
            <span class="tip-text">Context: <b>{{ selectedRegion.properties?.name || selectedRegion.id }}</b></span>
          </div>
          <el-button link type="primary" size="small" @click="clearSelection">Clear</el-button>
        </div>
      </Transition>

      <div class="input-card" :class="{ 'has-tip': selectedRegion || isTyping }">
        <el-input v-model="inputMsg" type="textarea" :rows="2" placeholder="Ask about the map..." resize="none"
          @keydown.enter.exact.prevent="handleHandleSend" />
        <div class="input-actions">
          <span class="input-tip"><b>Enter</b> send / <b>Shift+Enter</b> wrap</span>
          <el-button type="primary" :loading="isTyping" @click="handleHandleSend" :disabled="!inputMsg.trim()">
            <el-icon><Promotion /></el-icon>
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, reactive } from 'vue';
import { User, Promotion, Monitor, LocationInformation } from '@element-plus/icons-vue';
import MarkdownRender from 'markstream-vue';
import 'markstream-vue/index.css';
import './style.css';

// 导入提取的逻辑
import { useChatLogic } from './useChatLogic';

const emit = defineEmits(['refresh-map']);
const { 
  isTyping, currentStatus, debugInfo, selectedRegion, 
  clearSelection, sendMessage 
} = useChatLogic(emit);

// UI 独占状态
const inputMsg = ref('');
const chatRef = ref(null);
const showDebug = ref(false);
const messages = ref([
  { role: 'ai', content: 'Map system initialized. Select an object or ask a question.' }
]);

const scrollToBottom = async () => {
  await nextTick();
  if (chatRef.value) {
    chatRef.value.scrollTo({ top: chatRef.value.scrollHeight, behavior: 'smooth' });
  }
};

const handleHandleSend = async () => {
  const query = inputMsg.value.trim();
  if (!query || isTyping.value) return;

  // 1. UI 层添加用户消息
  messages.value.push({ role: 'user', content: query });
  inputMsg.value = '';
  
  // 2. 准备 AI 占位消息
  const aiMsg = reactive({ role: 'ai', content: '' });
  messages.value.push(aiMsg);
  await scrollToBottom();

  // 3. 调用业务逻辑层，传入更新回调
  await sendMessage(query, (content) => {
    aiMsg.content = content;
    scrollToBottom();
  });
};
</script>