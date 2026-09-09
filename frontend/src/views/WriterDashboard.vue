<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import api from '../services/api'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const articles = ref([])
const loading = ref(true)

const counts = computed(() => ({
  active: articles.value.filter(a => ['DRAFTING','AWAITING_EVALUATION','UNDER_REVIEW'].includes(a.status)).length,
  revision: articles.value.filter(a => a.status === 'REVISION_REQUESTED').length,
  approved: articles.value.filter(a => ['APPROVED','PUBLISHED'].includes(a.status)).length,
}))

onMounted(async () => {
  try {
    if (!auth.user) await auth.fetchUser()
    const { data } = await api.get('/editorial/articles/')
    articles.value = data.results ?? data
  } finally {
    loading.value = false
  }
})

function signOut() {
  auth.logout()
  router.push('/staff/login')
}
</script>

<template>
  <div class="wrap">
    <header>
      <h2>WRITER DASHBOARD</h2>
      <button class="out" @click="signOut">Sign out</button>
    </header>
    <p class="hi">Welcome back, {{ auth.user?.first_name }}!</p>

    <div class="cards">
      <div class="card"><b>{{ counts.active }}</b><span>ACTIVE</span></div>
      <div class="card"><b>{{ counts.revision }}</b><span>REVISION</span></div>
      <div class="card"><b>{{ counts.approved }}</b><span>APPROVED</span></div>
    </div>

    <h3>My latest activity</h3>
    <p v-if="loading">Loading…</p>
    <p v-else-if="!articles.length" class="empty">No articles yet.</p>
    <ul v-else>
      <li v-for="a in articles" :key="a.id">
        <span class="t">{{ a.title }}</span>
        <em>{{ a.status }}</em>
        <b v-if="a.latest_score">{{ a.latest_score }}</b>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.wrap { max-width: 760px; margin: 40px auto; font-family: system-ui; padding: 0 16px; }
header { display: flex; justify-content: space-between; align-items: center; }
h2 { margin: 0; letter-spacing: 1px; }
.out { border: 1px solid #ccc; background: #fff; border-radius: 6px; padding: 6px 12px; cursor: pointer; }
.hi { color: #555; }
.cards { display: flex; gap: 12px; margin: 22px 0; }
.card { flex: 1; border: 1px solid #e3e3e3; border-radius: 8px; padding: 18px; text-align: center; }
.card b { display: block; font-size: 30px; }
.card span { font-size: 11px; color: #888; letter-spacing: .5px; }
ul { list-style: none; padding: 0; }
li { display: flex; justify-content: space-between; align-items: center; gap: 12px;
     border-bottom: 1px solid #eee; padding: 13px 0; }
.t { flex: 1; }
em { font-size: 11px; color: #888; font-style: normal; }
.empty { color: #888; }
</style>
