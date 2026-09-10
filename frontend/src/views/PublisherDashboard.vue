<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import api from '../services/api'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()

const issues = ref([])
const standalone = ref([])
const loading = ref(true)
const error = ref('')
const busy = ref(null)

const creating = ref(false)
const form = ref({ number: '', title: '', target_release_date: '' })

const live = computed(() => issues.value.filter(i => i.status === 'PUBLISHED'))
const inProgress = computed(() =>
  issues.value.filter(i => !['PUBLISHED', 'ARCHIVED'].includes(i.status)))

async function load() {
  const [i, a] = await Promise.all([
    api.get('/publication/issues/'),
    api.get('/editorial/articles/'),
  ])
  issues.value = i.data.results ?? i.data
  standalone.value = (a.data.results ?? a.data)
    .filter(x => x.status === 'APPROVED' && !x.issue)
  loading.value = false
}

onMounted(async () => {
  if (!auth.user) await auth.fetchUser()
  await load()
})

async function createIssue() {
  error.value = ''
  if (!form.value.number || !form.value.title) {
    error.value = 'Issue number and title are required.'
    return
  }
  try {
    await api.post('/publication/issues/', {
      number: form.value.number,
      title: form.value.title,
      target_release_date: form.value.target_release_date || null,
    })
    form.value = { number: '', title: '', target_release_date: '' }
    creating.value = false
    await load()
  } catch (e) {
    error.value = e.response?.data?.number?.[0] || 'Could not create the issue.'
  }
}

async function publishStandalone(a) {
  error.value = ''
  busy.value = `a${a.id}`
  try { await api.post(`/editorial/articles/${a.id}/publish/`); await load() }
  catch (e) { error.value = e.response?.data?.detail || 'Publishing failed.' }
  finally { busy.value = null }
}

function signOut() { auth.logout(); router.push('/staff/login') }

const pct = (i) => i.total_articles
  ? Math.round((i.approved_articles / i.total_articles) * 100) : 0
</script>

<template>
  <div class="wrap">
    <header>
      <h2>PUBLISHER PIPELINE</h2>
      <button class="out" @click="signOut">Sign out</button>
    </header>
    <p class="hi">Welcome back, {{ auth.user?.first_name }}!</p>

    <p v-if="error" class="err">{{ error }}</p>

    <div class="head">
      <h3>Issues in preparation</h3>
      <button class="new" @click="creating = !creating">
        {{ creating ? 'Cancel' : '+ New Issue' }}
      </button>
    </div>

    <div v-if="creating" class="form">
      <div class="row">
        <label>NUMBER<input v-model="form.number" type="number" placeholder="13" /></label>
        <label class="grow">TITLE<input v-model="form.title" placeholder="The April Issue" /></label>
        <label>TARGET DATE<input v-model="form.target_release_date" type="date" /></label>
      </div>
      <button class="primary" @click="createIssue">Create Issue</button>
    </div>

    <p v-if="loading">Loading…</p>
    <p v-else-if="!inProgress.length" class="empty">No issues in preparation.</p>

    <div v-for="i in inProgress" :key="i.id" class="issue"
         @click="router.push(`/publisher/issue/${i.id}`)">
      <div class="itop">
        <div>
          <span class="num">Issue #{{ i.number }}</span>
          <span class="title">{{ i.title }}</span>
        </div>
        <span class="badge" :class="i.is_ready ? 'ready' : 'wip'">
          {{ i.is_ready ? 'Ready to publish' : 'In preparation' }}
        </span>
      </div>
      <div class="bar">
        <div class="track"><i :style="{ width: pct(i) + '%' }"
             :class="{ full: i.is_ready }"></i></div>
        <small>{{ i.approved_articles }} of {{ i.total_articles }} articles ready</small>
      </div>
      <div class="flags">
        <span :class="i.has_approved_design ? 'ok' : 'no'">
          {{ i.has_approved_design ? '✓' : '○' }} Layout approved
        </span>
        <span v-if="i.target_release_date" class="date">
          Target {{ i.target_release_date }}
        </span>
      </div>
    </div>

    <template v-if="standalone.length">
      <h3>Standalone articles</h3>
      <p class="note">
        Approved articles not assigned to an issue. These publish on their own.
      </p>
      <ul>
        <li v-for="a in standalone" :key="a.id">
          <div class="meta">
            <span class="t">{{ a.title }}</span>
            <em>{{ a.writer_name }} · {{ a.category || 'Uncategorised' }}</em>
          </div>
          <button class="pub" :disabled="busy === `a${a.id}`"
                  @click="publishStandalone(a)">
            {{ busy === `a${a.id}` ? 'Publishing…' : 'Publish' }}
          </button>
        </li>
      </ul>
    </template>

    <template v-if="live.length">
      <h3>Published issues</h3>
      <ul>
        <li v-for="i in live" :key="i.id">
          <div class="meta">
            <span class="t">Issue #{{ i.number }} · {{ i.title }}</span>
            <em>{{ i.total_articles }} articles</em>
          </div>
          <router-link :to="`/publisher/issue/${i.id}`" class="view">View</router-link>
        </li>
      </ul>
    </template>
  </div>
</template>

<style scoped>
.wrap { max-width: 820px; margin: 40px auto; font-family: system-ui; padding: 0 16px 70px; }
header { display: flex; justify-content: space-between; align-items: center; }
h2 { margin: 0; letter-spacing: 1px; }
.out { border: 1px solid #ccc; background: #fff; border-radius: 6px; padding: 6px 12px; cursor: pointer; }
.hi { color: #555; }
.head { display: flex; justify-content: space-between; align-items: center; margin-top: 26px; }
h3 { margin: 26px 0 10px; font-size: 15px; }
.head h3 { margin: 0; }
.new { border: 1px solid #ccc; background: #fff; border-radius: 6px;
       padding: 7px 14px; font-size: 13px; cursor: pointer; }
.form { border: 1px solid #e6e6e6; border-radius: 8px; padding: 16px;
        background: #fafafa; margin: 12px 0 18px; }
.row { display: flex; gap: 12px; }
.row label { font-size: 11px; color: #555; letter-spacing: .5px; }
.row label.grow { flex: 1; }
input { width: 100%; padding: 9px; border: 1px solid #ccc; border-radius: 6px;
        font-size: 13px; margin-top: 5px; }
.primary { width: 100%; margin-top: 12px; padding: 11px; border: 0; background: #1a2744;
           color: #fff; border-radius: 6px; font-weight: 600; cursor: pointer; }
.issue { border: 1px solid #eee; border-radius: 10px; padding: 16px;
         margin-bottom: 10px; cursor: pointer; }
.issue:hover { border-color: #ccc; }
.itop { display: flex; justify-content: space-between; align-items: flex-start; }
.num { display: block; font-size: 12px; color: #888; }
.title { font-weight: 600; font-size: 16px; }
.badge { font-size: 11px; padding: 4px 11px; border-radius: 12px; }
.badge.ready { background: #eaf7f0; color: #1c6b45; }
.badge.wip { background: #eef2f7; color: #445; }
.bar { margin-top: 14px; }
.track { height: 7px; background: #eee; border-radius: 4px; overflow: hidden; }
.track i { display: block; height: 100%; background: #4a7fb5; }
.track i.full { background: #2e9e63; }
.bar small { display: block; margin-top: 6px; font-size: 12px; color: #888; }
.flags { display: flex; gap: 16px; margin-top: 10px; font-size: 12px; }
.flags .ok { color: #1c6b45; }
.flags .no { color: #999; }
.flags .date { color: #888; margin-left: auto; }
.note { margin: 0 0 10px; font-size: 12px; color: #888; }
ul { list-style: none; padding: 0; margin: 0; }
li { display: flex; justify-content: space-between; align-items: center;
     border: 1px solid #eee; border-radius: 8px; padding: 12px 14px; margin-bottom: 8px; }
.meta { display: flex; flex-direction: column; gap: 3px; }
.t { font-weight: 600; font-size: 14px; }
em { font-size: 12px; color: #888; font-style: normal; }
.pub { border: 0; background: #1a2744; color: #fff; padding: 9px 18px;
       border-radius: 6px; font-weight: 600; cursor: pointer; }
.pub:disabled { opacity: .55; }
.view { font-size: 13px; color: #4a7fb5; }
.empty { color: #888; font-size: 14px; }
.err { color: #c00; font-size: 13px; }
</style>
