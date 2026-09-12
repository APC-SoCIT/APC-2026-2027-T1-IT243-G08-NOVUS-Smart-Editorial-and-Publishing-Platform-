<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
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

function onKey(e) {
  if (e.key === 'Escape' && open.value) {
    open.value = false
    document.querySelector('.bell')?.focus()
  }
}

onMounted(() => {
  document.addEventListener('keydown', onKey)
  loadCount()
  timer = setInterval(loadCount, 30000)
})
onUnmounted(() => {
  clearInterval(timer)
  document.removeEventListener('keydown', onKey)
})

const ago = (d) => {
  const mins = Math.floor((Date.now() - new Date(d)) / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

const urgent = ['DEADLINE_PASSED', 'RETURNED_BY_AI', 'REVISION', 'DESIGN_REVISION']

const filter = ref('all')
const FILTERS = [
  { key: 'all', label: 'All' },
  { key: 'urgent', label: 'Needs action' },
  { key: 'unread', label: 'Unread' },
]

/* Grouped by recency rather than listed flat. Twelve kinds rendering
   identically meant a deadline warning read the same as a routine
   submission notice, and the one that mattered was hardest to find. */
const groups = computed(() => {
  let list = items.value
  if (filter.value === 'urgent') list = list.filter(n => urgent.includes(n.kind))
  if (filter.value === 'unread') list = list.filter(n => !n.is_read)

  const start = new Date(); start.setHours(0, 0, 0, 0)
  const week = new Date(start); week.setDate(start.getDate() - 7)

  const buckets = [
    { label: 'Today', items: [] },
    { label: 'This week', items: [] },
    { label: 'Earlier', items: [] },
  ]
  for (const n of list) {
    const d = new Date(n.created_at)
    if (d >= start) buckets[0].items.push(n)
    else if (d >= week) buckets[1].items.push(n)
    else buckets[2].items.push(n)
  }
  return buckets.filter(b => b.items.length)
})
</script>

<template>
  <div class="bell-wrap">
    <button class="bell" :class="{ active: open }"
            :aria-expanded="open" aria-haspopup="true"
            aria-controls="notif-panel"
            :aria-label="unread
              ? `Notifications, ${unread} unread`
              : 'Notifications, none unread'"
            @click="toggle">
      <svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24"
           fill="none" stroke="currentColor" stroke-width="1.8"
           stroke-linecap="round" stroke-linejoin="round">
        <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
        <path d="M13.73 21a2 2 0 0 1-3.46 0" />
      </svg>
      <span v-if="unread" class="badge" aria-hidden="true">
        {{ unread > 99 ? '99+' : unread }}
      </span>
    </button>

    <div v-if="open" id="notif-panel" class="panel"
         role="region" aria-label="Notifications">
      <div class="phead">
        <span>Notifications</span>
        <button v-if="unread" class="mark" @click="markAll">Mark all read</button>
      </div>

      <div class="filters" role="tablist" aria-label="Filter notifications">
        <button v-for="f in FILTERS" :key="f.key" role="tab"
                :aria-selected="filter === f.key"
                :class="{ on: filter === f.key }"
                @click="filter = f.key">{{ f.label }}</button>
      </div>

      <p v-if="!groups.length" class="empty">
        {{ filter === 'all' ? 'Nothing yet.' : 'Nothing here.' }}
      </p>

      <div v-else class="scroll">
        <template v-for="g in groups" :key="g.label">
          <p class="glabel">{{ g.label }}</p>
          <ul>
            <li v-for="n in g.items" :key="n.id"
            :class="{ unread: !n.is_read, urgent: urgent.includes(n.kind) }"
            tabindex="0" role="button"
            :aria-label="`${n.message}${n.is_read ? '' : ', unread'}`"
            @click="openItem(n)" @keyup.enter="openItem(n)"
            @keyup.space.prevent="openItem(n)">
          <p>{{ n.message }}</p>
          <small>{{ ago(n.created_at) }}</small>
            </li>
          </ul>
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped>
.bell-wrap { position: relative; }
.filters { display: flex; gap: 2px; padding: 8px 10px;
           border-bottom: 1px solid var(--nv-line); }
.filters button { flex: 1; background: none; border: 0; padding: 6px;
                  font-size: 12px; color: var(--nv-text-muted);
                  border-radius: var(--r-sm); cursor: pointer;
                  font-family: inherit; }
.filters button:hover { background: var(--nv-bg); }
.filters button.on { background: var(--nv-navy-2); color: #fff;
                     font-weight: 600; }
.scroll { max-height: 360px; overflow-y: auto; }
.glabel { margin: 0; padding: 8px 14px 4px; font-size: 11px;
          letter-spacing: .05em; text-transform: uppercase;
          color: var(--nv-text-faint); background: var(--nv-bg); }
.bell { position: relative; border: 1px solid var(--nv-line-strong); background: var(--nv-surface); border-radius: var(--r-sm);
        padding: 7px 13px; font-size: 13px; cursor: pointer;
        color: var(--nv-text); }
.bell.active { background: var(--nv-bg); border-color: var(--nv-text-faint); }
.badge { position: absolute; top: -7px; right: -7px; background: #c0392b; color: #fff;
         font-size: 10px; min-width: 18px; height: 18px; border-radius: 9px;
         display: inline-flex; align-items: center; justify-content: center; padding: 0 5px; }
.panel { position: absolute; right: 0; top: 38px; width: 320px; background: var(--nv-surface);
         border: 1px solid var(--nv-line); border-radius: 10px; z-index: 20;
         box-shadow: 0 8px 26px rgba(0,0,0,.10); overflow: hidden; }
.phead { display: flex; justify-content: space-between; align-items: center;
         padding: 11px 14px; border-bottom: 1px solid var(--nv-line); font-size: 12px;
         letter-spacing: .5px; text-transform: uppercase; color: var(--nv-text-muted); }
.mark { border: 0; background: none; color: var(--nv-accent); font-size: 11px; cursor: pointer; }
ul { list-style: none; margin: 0; padding: 0; max-height: 380px; overflow-y: auto; }
li { padding: 11px 14px; border-bottom: 1px solid var(--nv-line);
     cursor: pointer; color: var(--nv-text); }
li:hover { background: var(--nv-bg); }
li.unread { background: var(--nv-accent-soft); }
li.unread:hover { background: var(--nv-accent-soft); }
li.urgent p { color: var(--bad); }
li p { margin: 0 0 3px; font-size: 13px; line-height: 1.45; }
li small { font-size: 11px; color: var(--nv-text-faint); }
.empty { padding: 22px 14px; margin: 0; font-size: 13px; color: var(--nv-text-faint); text-align: center; }
</style>
