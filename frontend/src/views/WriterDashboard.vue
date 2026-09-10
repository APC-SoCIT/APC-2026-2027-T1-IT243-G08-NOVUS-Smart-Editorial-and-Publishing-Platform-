<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import api from '../services/api'
import { useAuthStore } from '../stores/auth'
import FilterBar from '../components/FilterBar.vue'
import StaffLayout from '../components/StaffLayout.vue'

const auth = useAuthStore()
const router = useRouter()
const articles = ref([])
const loading = ref(true)

const assignments = computed(() =>
  articles.value.filter(a => a.status === 'ASSIGNED'))

const counts = computed(() => ({
  active: articles.value.filter(a => ['ASSIGNED','DRAFTING','AWAITING_EVALUATION','UNDER_REVIEW'].includes(a.status)).length,
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

function open(a) {
  if (['ASSIGNED', 'DRAFTING', 'REVISION_REQUESTED'].includes(a.status)) {
    router.push(`/writer/compose/${a.id}`)
  }
}
function signOut() {
  auth.logout()
  router.push('/staff/login')
}
</script>

<template>
  <StaffLayout title="Writer dashboard" subtitle="Your assignments and submissions">
    <div class="cards">
      <div class="card"><b>{{ counts.active }}</b><span>ACTIVE</span></div>
      <div class="card"><b>{{ counts.revision }}</b><span>REVISION</span></div>
      <div class="card"><b>{{ counts.approved }}</b><span>APPROVED</span></div>
    </div>
<router-link to="/writer/compose" class="new-btn">+ New Submission</router-link>
    <FilterBar
      :statuses="['ASSIGNED','DRAFTING','UNDER_REVIEW',
                   'REVISION_REQUESTED','APPROVED','PUBLISHED']"
      :show-overdue="false"
      @change="applyFilters" />

    <h3>My latest activity</h3>
    <p v-if="loading">Loading…</p>
    <p v-else-if="!articles.length" class="empty">No articles yet.</p>
    <ul v-else>
      <li v-for="a in articles" :key="a.id"
          :class="{ clickable: ['DRAFTING','REVISION_REQUESTED'].includes(a.status) }"
          @click="open(a)">
        <span class="t">{{ a.title }}</span>
        <em>{{ a.status }}</em>
        <b v-if="a.latest_score">{{ a.latest_score }}</b>
      </li>
    </ul>
  </StaffLayout>
</template>

<style scoped>
header { display: flex; justify-content: space-between; align-items: center; }
h2 { margin: 0; letter-spacing: 1px; }
.hactions { display: flex; gap: 10px; align-items: center; }
.out { border: 1px solid #ccc; background: #fff; border-radius: 6px; padding: 6px 12px; cursor: pointer; }
.hi { color: #555; }
.cards { display: flex; gap: 12px; margin: 22px 0; }
.card { flex: 1; border: 1px solid #e3e3e3; border-radius: 8px; padding: 18px; text-align: center; }
.card b { display: block; font-size: 30px; }
.card span { font-size: 11px; color: #888; letter-spacing: .5px; }
ul { list-style: none; padding: 0; }
.assign { border: 1px solid #e0e6ef; background: #f7faff; border-radius: 8px;
          padding: 14px 16px; margin-bottom: 8px; cursor: pointer; }
.assign:hover { border-color: #b9c9e0; }
.atop { display: flex; justify-content: space-between; align-items: center; }
.brief { margin: 8px 0; font-size: 13px; color: #555; line-height: 1.55; }
.start { font-size: 12px; color: #4a7fb5; }
.due { font-size: 11px; padding: 4px 10px; border-radius: 12px;
       background: #eef2f7; color: #445; }
.due.over { background: #fbe6e6; color: #a33; }
li.clickable { cursor: pointer; }
li.clickable:hover { background: #fafafa; }
li { display: flex; justify-content: space-between; align-items: center; gap: 12px;
     border-bottom: 1px solid #eee; padding: 13px 0; }
.t { flex: 1; }
em { font-size: 11px; color: #888; font-style: normal; }
.empty { color: #888; }
.new-btn { display: block; text-align: center; padding: 12px; background: #1a2744;
           color: #fff; border-radius: 6px; text-decoration: none; font-weight: 600; margin-bottom: 20px; }
</style>
