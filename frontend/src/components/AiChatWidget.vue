<template>
  <div class="ai-chat-widget" :class="{ open: isOpen, thinking: isThinking }">
    <Transition name="ai-chat-expand">
      <section v-if="isOpen" class="ai-chat-panel" :aria-label="labels.chatAria">
        <header class="ai-chat-header">
          <div>
            <strong>Critical AI</strong>
            <span>{{ labels.subtitle }}</span>
          </div>
          <button type="button" class="ai-chat-icon-button" :aria-label="labels.close" @click="isOpen = false">
            <X :size="18" />
          </button>
        </header>

        <div ref="messageList" class="ai-chat-messages">
          <div v-for="message in messages" :key="message.id" class="ai-chat-message" :class="message.role">
            <p>
              {{ message.text }}<span v-if="message.streaming" class="ai-chat-stream-cursor"></span>
            </p>
          </div>
          <div v-if="isAwaitingReply" class="ai-chat-message assistant typing">
            <p class="ai-chat-typing-indicator" aria-label="답변 작성 중">
              <span></span>
              <span></span>
              <span></span>
            </p>
          </div>
        </div>

        <form class="ai-chat-form" @submit.prevent="sendMessage">
          <input v-model="draft" type="text" :placeholder="labels.placeholder" />
          <button type="submit" :aria-label="labels.send" :disabled="!draft.trim() || isThinking">
            <ArrowUp :size="20" />
          </button>
        </form>
      </section>
    </Transition>

    <button type="button" class="ai-chat-fab" :aria-label="isOpen ? labels.close : labels.open" @click="toggleChat">
      <span class="chatbot-face" aria-hidden="true">
        <span class="chatbot-eye left"></span>
        <span class="chatbot-eye right"></span>
        <span class="chatbot-mouth"></span>
      </span>
    </button>
  </div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { ArrowUp, X } from 'lucide-vue-next'
import { recommendationsApi } from '../api/recommendations'
import { useAuthStore } from '../stores/auth'

const labels = {
  chatAria: '\u0041\u0049 \ucc57\ubd07',
  subtitle: '\ud560\uc778, \uac00\uaca9, \uac8c\uc784 \ucd94\ucc9c\uc744 \ubb3c\uc5b4\ubcf4\uc138\uc694.',
  close: '\u0041\u0049 \ucc57 \ub2eb\uae30',
  open: '\u0041\u0049 \ucc57 \uc5f4\uae30',
  send: '\uba54\uc2dc\uc9c0 \ubcf4\ub0b4\uae30',
  placeholder: '\uac8c\uc784 \ucd94\ucc9c\uc774\ub098 \ud560\uc778 \uc815\ubcf4\ub97c \ubb3c\uc5b4\ubcf4\uc138\uc694',
  emptyReply: '\ub2f5\ubcc0\uc744 \ub9cc\ub4e4\uc9c0 \ubabb\ud588\uc5b4\uc694. \uc7a0\uc2dc \ud6c4 \ub2e4\uc2dc \uc2dc\ub3c4\ud574 \uc8fc\uc138\uc694.',
  requestFailed: '\ucc57\ubd07 \uc694\uccad\uc5d0 \uc2e4\ud328\ud588\uc5b4\uc694. \ubc31\uc5d4\ub4dc \uc11c\ubc84\uc640 \u0047\u004d\u0053 \uc124\uc815\uc744 \ud655\uc778\ud574 \uc8fc\uc138\uc694.',
}

const TYPE_DELAY_MS = 18

const auth = useAuthStore()
const isOpen = ref(false)
const draft = ref('')
const isThinking = ref(false)
const isAwaitingReply = ref(false)
const messageList = ref(null)
const userName = computed(() => auth.user?.display_name || auth.user?.username || auth.user?.email?.split('@')[0] || '\uc0ac\uc6a9\uc790')
const greetingText = computed(
  () =>
    `\uc548\ub155\ud558\uc138\uc694 ${userName.value}\ub2d8! \ud560\uc778, \uac00\uaca9 \ucd94\uc774, \uc7a5\ub974 \ucde8\ud5a5\uc744 \uae30\uc900\uc73c\ub85c \uac8c\uc784 \uc120\ud0dd\uc744 \ub3c4\uc640\ub4dc\ub9b4\uac8c\uc694.`,
)
const messages = ref([
  {
    id: 1,
    role: 'assistant',
    text: greetingText.value,
  },
])

if (!auth.user) auth.fetchMe()

watch(greetingText, (nextGreeting, previousGreeting) => {
  const firstMessage = messages.value[0]
  if (firstMessage?.id === 1 && firstMessage.text === previousGreeting) {
    firstMessage.text = nextGreeting
  }
})

const scrollToBottom = async () => {
  await nextTick()
  if (!messageList.value) return
  messageList.value.scrollTop = messageList.value.scrollHeight
}

const wait = (ms) => new Promise((resolve) => window.setTimeout(resolve, ms))

const typeAssistantReply = async (reply) => {
  const assistantMessage = {
    id: Date.now() + 1,
    role: 'assistant',
    text: '',
    streaming: true,
  }
  messages.value.push(assistantMessage)
  const messageIndex = messages.value.length - 1
  await scrollToBottom()

  const characters = Array.from(reply)
  for (const character of characters) {
    const currentMessage = messages.value[messageIndex]
    if (!currentMessage) break

    currentMessage.text = `${currentMessage.text}${character}`
    if (currentMessage.text.length % 3 === 0 || character === '\n') {
      await scrollToBottom()
    }
    await wait(TYPE_DELAY_MS)
  }

  const currentMessage = messages.value[messageIndex]
  if (currentMessage) currentMessage.streaming = false
  await scrollToBottom()
}

const toggleChat = () => {
  isOpen.value = !isOpen.value
  if (isOpen.value) scrollToBottom()
}

const chatHistory = () =>
  messages.value
    .filter((message) => ['user', 'assistant'].includes(message.role))
    .slice(-8)
    .map((message) => ({ role: message.role, text: message.text }))

const sendMessage = async () => {
  const text = draft.value.trim()
  if (!text || isThinking.value) return

  messages.value.push({ id: Date.now(), role: 'user', text })
  draft.value = ''
  isThinking.value = true
  isAwaitingReply.value = true
  await scrollToBottom()

  try {
    const result = await recommendationsApi.chat(text, chatHistory())
    isAwaitingReply.value = false
    await typeAssistantReply(result.reply || labels.emptyReply)
  } catch (error) {
    isAwaitingReply.value = false
    await typeAssistantReply(error.message || labels.requestFailed)
  } finally {
    isAwaitingReply.value = false
    isThinking.value = false
    await scrollToBottom()
  }
}
</script>
