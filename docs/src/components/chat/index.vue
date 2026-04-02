<template>
  <div class="chat-container-fixed">
    <header class="chat-header">
      <div class="header-left">
        <span class="title-main">AI Map Assistant</span>
      </div>
      <div class="header-right" style="display:flex; align-items:center; gap:10px;">
        <ThemeSwitch />
        <el-button :type="showDebug ? 'warning' : 'info'" size="small" link @click="showDebug = !showDebug">
          <el-icon><Monitor /></el-icon>
        </el-button>
      </div>
    </header>

    <Transition name="el-zoom-in-top">
      <div v-if="showDebug" class="debug-panel" style="max-height: 150px; overflow-y: auto; background: #1a1a1a; padding: 10px;">
        <pre style="color: #00ff00; font-size: 11px; margin:0;">{{ JSON.stringify(debugInfo, null, 2) }}</pre>
      </div>
    </Transition>

    <div class="chat-viewport" ref="chatRef">
      <div class="message-list">
        <div v-for="(msg, index) in messages" :key="index" :class="['msg-row', msg.role]">
          <div class="avatar-wrapper">
            <el-avatar :size="24" :src="msg.role === 'ai' ? 'https://api.dicebear.com/7.x/bottts/svg?seed=Felix' : ''">
              <el-icon v-if="msg.role === 'user'"><User /></el-icon>
            </el-avatar>
          </div>
          <div class="msg-content-wrapper">
            <div class="bubble">
              <template v-if="msg.role === 'ai'">
                <MarkdownRender v-if="msg.content" :content="msg.content" />
                <div v-else class="mini-typing">
                  <span></span><span></span><span></span>
                </div>
              </template>
              <template v-else>{{ msg.content }}</template>
            </div>
            <div v-if="msg.role === 'ai' && msg.content" class="msg-ops">
              <el-button link size="small" @click="handleCopy(msg.content)">
                <el-icon><CopyDocument /></el-icon>
                <span style="font-size: 11px; margin-left: 4px;">Copy Raw</span>
              </el-button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <footer class="input-fixed-bottom">
      <Transition name="el-zoom-in-top">
        <div v-if="isTyping" class="status-bar">
          <span class="status-text">{{ currentStatus || 'Thinking...' }}</span>
        </div>
      </Transition>

      <div class="input-card">
        <el-input 
          v-model="inputMsg" 
          type="textarea" 
          :rows="2" 
          placeholder="Ask a question..." 
          resize="none"
          @keydown.enter.exact.prevent="handleSend" 
        />
        <div class="input-actions" style="display:flex; justify-content: space-between; align-items:center; margin-top: 4px;">
                <Transition name="el-zoom-in-top">
        <div v-if="selectedRegion" class="selection-tip">
          <span style="font-size: 12px;"><el-icon><LocationInformation /></el-icon> Context: <b>{{ selectedRegion.properties?.name || 'Selected' }}</b></span>
          <el-button link type="primary" size="small" @click="clearSelection">Clear</el-button>
        </div>
      </Transition>
          <el-button type="primary" size="small" :loading="isTyping" @click="handleSend" :disabled="!inputMsg.trim()">
            <el-icon><Promotion /></el-icon>
          </el-button>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { ref, nextTick, reactive } from 'vue';
import { ElMessage } from 'element-plus';
import { User, Promotion, Monitor, CopyDocument, LocationInformation } from '@element-plus/icons-vue';
import MarkdownRender from 'markstream-vue';
import 'markstream-vue/index.css';
import './style.css';
import ThemeSwitch from '@/components/ThemeSwitch.vue';
import { useChatLogic } from './useChatLogic';

const emit = defineEmits(['refresh-map']);
const { isTyping, currentStatus, debugInfo, selectedRegion, clearSelection, sendMessage } = useChatLogic(emit);

const inputMsg = ref('');
const chatRef = ref(null);
const showDebug = ref(false);
const messages = ref([{ role: 'ai', content: 'System initialized. Ready for map analysis.' }]);

const scrollToBottom = async () => {
  await nextTick();
  if (chatRef.value) {
    chatRef.value.scrollTop = chatRef.value.scrollHeight;
  }
};

const handleCopy = async (text) => {
  try {
    await navigator.clipboard.writeText(text);
    ElMessage.success({ message: 'Copied', duration: 1000 });
  } catch (err) {
    ElMessage.error('Failed to copy');
  }
};

const handleSend = async () => {
  const query = inputMsg.value.trim();
  if (!query || isTyping.value) return;

  messages.value.push({ role: 'user', content: query });
  inputMsg.value = '';
  
  const aiMsg = reactive({ role: 'ai', content: '' });
  messages.value.push(aiMsg);
  await scrollToBottom();

  await sendMessage(query, (content) => {
    aiMsg.content = content; // MarkdownRender 组件会自动处理内容更新带来的“流式”视觉感
    scrollToBottom();
  });
};
</script>