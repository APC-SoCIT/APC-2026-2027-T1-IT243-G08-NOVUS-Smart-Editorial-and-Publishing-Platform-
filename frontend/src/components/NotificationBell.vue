<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../services/api'

const router = useRouter()
const open = ref(false)
const items = ref([])
const unread = ref(0)
let timer = null

async function loadCount() {
  try {
    const { data } = await api.get('/notifications/unread_count/')
    unread.value = data.unread
  } catch { /* not signed in yet */ }
}

async function loadList() {
  const { data } = await api.get('/notifications/')
  items.value = (data.results ?? data).slice(0, 12)
}

async function toggle() {
  open.value = !open.value
  if (open.value) await loadList()
}

async function openItem(n) {
  if (!n.is_read) {
    await api.post(`/notifications/${n.id}/read/`)
    unread.value = Math.max(0, unread.value - 1)
    n.is_read = true
  }
  open.value = false
  if (n.link) router.push(n.link)
}

async function markAll() {
  await api.post('/notifications/read-all/')
  unread.value = 0
  items.value.forEach(n => (n.is_read = true))
}

onMounted(() => {
  loadCount()
  timer = setInterval(loadCount, 30000)
})
onUnmounted(() => clearInterval(timer))

const ago = (d) => {
  const mins = Math.floor((Date.now() - new Date(d)) / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

const urgent = ['DEADLINE_PASSED', 'RETURNED_BY_AI', 'REVISION', 'DESIGN_REVISION']
</script>

<template>
  <div class="bell-wrap">
    <button class="bell" @click="toggle" :class="{ active: open }">
      Notifications
      <span v-if="unread" class="badge">{{ unread > 99 ? '99+' : unread }}</span>
    </button>

    <div v-if="open" class="panel">
      <div class="phead">
        <span>Notifications</span>
        <button v-if="unread" class="mark" @click="markAll">Mark all read</button>
      </div>

      <p v-if="!items.length" class="empty">Nothing yet.</p>
      <ul v-else>
        <li v-for="n in items" :key="n.id"
            :class="{ unread: !n.is_read, urgent: urgent.includes(n.kind) }"
            @click="openItem(n)">
          <p>{{ n.message }}</p>
          <small>{{ ago(n.created_at) }}</small>
        </li>
      </ul>
    </div>
  </div>
</template>

<style scoped>
.bell-wrap { position: relative; }
.bell { position: relative; border: 1px solid #ccc; background: #fff; border-radius: 6px;
        padding: 6px 12px; font-size: 13px; cursor: pointer; }
.bell.active { background: #f2f2f2; }
.badge { position: absolute; top: -7px; right: -7px; background: #c0392b; color: #fff;
         font-size: 10px; min-width: 18px; height: 18px; border-radius: 9px;
         display: inline-flex; align-items: center; justify-content: center; padding: 0 5px; }
.panel { position: absolute; right: 0; top: 38px; width: 320px; background: #fff;
         border: 1px solid #e2e2e2; border-radius: 10px; z-index: 20;
         box-shadow: 0 8px 26px rgba(0,0,0,.10); overflow: hidden; }
.phead { display: flex; justify-content: space-between; align-items: center;
         padding: 11px 14px; border-bottom: 1px solid #eee; font-size: 12px;
         letter-spacing: .5px; text-transform: uppercase; color: #666; }
.mark { border: 0; background: none; color: #4a7fb5; font-size: 11px; cursor: pointer; }
ul { list-style: none; margin: 0; padding: 0; max-height: 380px; overflow-y: auto; }
li { padding: 11px 14px; border-bottom: 1px solid #f2f2f2; cursor: pointer; }
li:hover { background: #fafafa; }
li.unread { background: #f6f9fd; }
li.unread:hover { background: #eef4fb; }
li.urgent p { color: #a33; }
li p { margin: 0 0 3px; font-size: 13px; line-height: 1.45; }
li small { font-size: 11px; color: #999; }
.empty { padding: 22px 14px; margin: 0; font-size: 13px; color: #999; text-align: center; }
</style>
