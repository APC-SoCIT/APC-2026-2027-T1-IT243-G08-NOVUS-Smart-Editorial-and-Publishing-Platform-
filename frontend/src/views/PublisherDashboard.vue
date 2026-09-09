<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import api from '../services/api'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const articles = ref([])
const loading = ref(true)
const busy = ref(null)
const error = ref('')

const ready = computed(() => articles.value.filter(a => a.status === 'APPROVED'))
const live = computed(() => articles.value.filter(a => a.status === 'PUBLISHED'))
const inProgress = computed(() =>
  articles.value.filter(a => ['DRAFTING', 'UNDER_REVIEW', 'REVISION_REQUESTED'].includes(a.status)))

async function load() {
  const { data } = await api.get('/editorial/articles/')
  articles.value = data.results ?? data
  loading.value = false
}
onMounted(async () => {
  if (!auth.user) await auth.fetchUser()
  await load()
})

async function publish(a) {
  error.value = ''
  busy.value = a.id
  try {
    await api.post(`/editorial/articles/${a.id}/publish/`)
    await load()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Publishing failed.'
  } finally { busy.value = null }
}

function signOut() { auth.logout(); router.push('/staff/login') }
</script>

<template>
  <div class="wrap">
    <header>
      <h2>PUBLISHER PIPELINE</h2>
      <button class="out" @click="signOut">Sign out</button>
    </header>
    <p class="hi">Welcome back, {{ auth.user?.first_name }}! Here's your publishing overview.</p>

    <div class="cards">
      <div class="card"><b>{{ ready.length }}</b><span>APPROVED</span></div>
      <div class="card"><b>{{ inProgress.length }}</b><span>IN PROGRESS</span></div>
      <div class="card"><b>{{ live.length }}</b><span>PUBLISHED</span></div>
    </div>

    <p v-if="error" class="err">{{ error }}</p>

    <h3>Ready to publish</h3>
    <p v-if="loading">Loading…</p>
    <p v-else-if="!ready.length" class="empty">Nothing approved yet.</p>
    <ul v-else>
      <li v-for="a in ready" :key="a.id">
        <div class="meta">
          <span class="t">{{ a.title }}</span>
          <em>{{ a.writer_name }} · {{ a.category || 'Uncategorised' }}</em>
        </div>
        <button class="pub" :disabled="busy === a.id" @click="publish(a)">
          {{ busy === a.id ? 'Publishing…' : 'Publish' }}
        </button>
      </li>
    </ul>

    <h3>Live on the portal</h3>
    <p v-if="!live.length" class="empty">Nothing published yet.</p>
    <ul v-else>
      <li v-for="a in live" :key="a.id">
        <div class="meta">
          <span class="t">{{ a.title }}</span>
          <em>{{ a.writer_name }} · published</em>
        </div>
        <a class="view" :href="`/read/${a.id}`" target="_blank">View</a>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.wrap { max-width: 820px; margin: 40px auto; font-family: system-ui; padding: 0 16px 60px; }
header { display: flex; justify-content: space-between; align-items: center; }
h2 { margin: 0; letter-spacing: 1px; }
.out { border: 1px solid #ccc; background: #fff; border-radius: 6px; padding: 6px 12px; cursor: pointer; }
.hi { color: #555; }
.cards { display: flex; gap: 12px; margin: 22px 0; }
.card { flex: 1; border: 1px solid #e3e3e3; border-radius: 8px; padding: 18px; text-align: center; }
.card b { display: block; font-size: 30px; }
.card span { font-size: 11px; color: #888; letter-spacing: .5px; }
h3 { margin: 28px 0 10px; font-size: 15px; }
ul { list-style: none; padding: 0; margin: 0; }
li { display: flex; justify-content: space-between; align-items: center; gap: 14px;
     border: 1px solid #eee; border-radius: 8px; padding: 12px 14px; margin-bottom: 8px; }
.meta { display: flex; flex-direction: column; gap: 3px; }
.t { font-weight: 600; }
em { font-size: 12px; color: #888; font-style: normal; }
.pub { border: 0; background: #1a2744; color: #fff; padding: 9px 20px;
       border-radius: 6px; font-weight: 600; cursor: pointer; }
.pub:disabled { opacity: .55; }
.view { font-size: 13px; color: #4a7fb5; }
.empty { color: #888; font-size: 14px; }
.err { color: #c00; font-size: 13px; }
</style>
