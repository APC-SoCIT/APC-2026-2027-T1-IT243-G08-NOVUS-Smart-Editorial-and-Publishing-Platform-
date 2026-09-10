<script setup>
import { ref, onMounted } from 'vue'
import api from '../services/api'
import { useAuthStore } from '../stores/auth'

const props = defineProps({
  articleId: { type: [Number, String], required: true },
})

const auth = useAuthStore()
const messages = ref([])
const draft = ref('')
const loading = ref(true)
const sending = ref(false)
const error = ref('')

async function load() {
  const { data } = await api.get('/messages/', {
    params: { article: props.articleId },
  })
  messages.value = data.results ?? data
  loading.value = false
}
onMounted(load)

async function send() {
  if (!draft.value.trim()) return
  error.value = ''
  sending.value = true
  try {
    await api.post('/messages/', {
      article: props.articleId,
      body: draft.value.trim(),
    })
    draft.value = ''
    await load()
  } catch {
    error.value = 'Could not send.'
  } finally { sending.value = false }
}

const mine = (m) => m.sender === auth.user?.id
const role = (r) => (r || '').replace('_', ' ').toLowerCase()
const ago = (d) => {
  const mins = Math.floor((Date.now() - new Date(d)) / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return new Date(d).toLocaleDateString()
}
</script>

<template>
  <div class="thread">
    <h5>Discussion</h5>
    <p class="hint">
      For questions and clarifications. Formal revision instructions go through
      revision notes, which change the article's status.
    </p>

    <p v-if="loading" class="muted">Loading…</p>
    <p v-else-if="!messages.length" class="muted">No messages yet.</p>

    <div v-else class="list">
      <div v-for="m in messages" :key="m.id" class="msg" :class="{ mine: mine(m) }">
        <div class="bubble">
          <div class="who">
            <b>{{ mine(m) ? 'You' : m.sender_name }}</b>
            <span class="role">{{ role(m.sender_role) }}</span>
            <small>{{ ago(m.created_at) }}</small>
          </div>
          <p>{{ m.body }}</p>
        </div>
      </div>
    </div>

    <div class="compose">
      <textarea v-model="draft" rows="2" maxlength="2000"
                placeholder="Write a message…"
                @keydown.ctrl.enter="send"></textarea>
      <button :disabled="sending || !draft.trim()" @click="send">
        {{ sending ? 'Sending…' : 'Send' }}
      </button>
    </div>
    <p v-if="error" class="err">{{ error }}</p>
  </div>
</template>

<style scoped>
.thread { border: 1px solid #e6e6e6; border-radius: 8px; padding: 16px; margin-top: 24px; }
h5 { margin: 0 0 5px; font-size: 12px; letter-spacing: .5px;
     text-transform: uppercase; color: #555; }
.hint { margin: 0 0 14px; font-size: 12px; color: #999; line-height: 1.5; }
.muted { color: #999; font-size: 13px; }
.list { max-height: 320px; overflow-y: auto; margin-bottom: 14px; }
.msg { display: flex; margin-bottom: 10px; }
.msg.mine { justify-content: flex-end; }
.bubble { max-width: 80%; background: #f4f6f8; border-radius: 10px; padding: 10px 13px; }
.msg.mine .bubble { background: #e8f0fa; }
.who { display: flex; gap: 7px; align-items: baseline; margin-bottom: 4px; }
.who b { font-size: 13px; }
.role { font-size: 10px; text-transform: uppercase; letter-spacing: .5px; color: #8a97a8; }
.who small { font-size: 11px; color: #aaa; margin-left: auto; }
.bubble p { margin: 0; font-size: 13px; line-height: 1.55; white-space: pre-wrap; }
.compose { display: flex; gap: 8px; }
textarea { flex: 1; padding: 9px; border: 1px solid #ccc; border-radius: 6px;
           font-family: inherit; font-size: 13px; resize: vertical; }
button { border: 0; background: #1a2744; color: #fff; border-radius: 6px;
         padding: 0 20px; font-weight: 600; cursor: pointer; }
button:disabled { opacity: .45; }
.err { color: #c00; font-size: 13px; margin: 8px 0 0; }
</style>
