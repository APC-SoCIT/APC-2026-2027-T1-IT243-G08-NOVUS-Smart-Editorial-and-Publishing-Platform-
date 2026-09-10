<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import api from '../services/api'
import { useAuthStore } from '../stores/auth'
import StaffLayout from '../components/StaffLayout.vue'
import DesignReview from '../components/DesignReview.vue'
import PipelinePanel from '../components/PipelinePanel.vue'
import FilterBar from '../components/FilterBar.vue'
import AssignArticle from '../components/AssignArticle.vue'

const auth = useAuthStore()
const router = useRouter()
const articles = ref([])
const loading = ref(true)

const pending = computed(() => articles.value.filter(a => a.status === 'UNDER_REVIEW'))
const returned = computed(() => articles.value.filter(a => a.returned_by_ai))
const assigned = computed(() =>
  articles.value.filter(a => ['ASSIGNED', 'DRAFTING'].includes(a.status)))
const approved = computed(() =>
  articles.value.filter(a => ['APPROVED', 'PUBLISHED'].includes(a.status)))

const filters = ref({})

async function load() {
  const { data } = await api.get('/editorial/articles/', { params: filters.value })
  articles.value = data.results ?? data
}

function applyFilters(f) {
  filters.value = f
  load()
}

onMounted(async () => {
  try {
    if (!auth.user) await auth.fetchUser()
    await load()
  } finally { loading.value = false }
})

function signOut() { auth.logout(); router.push('/staff/login') }
const scoreClass = (s) => s === null ? 'none' : s >= 70 ? 'good' : 'bad'
</script>

<template>
  <StaffLayout title="Editor dashboard" subtitle="Pipeline, reviews, and layouts">
    <div class="cards">
      <div class="card"><b>{{ articles.length }}</b><span>ARTICLES TOTAL</span></div>
      <div class="card"><b>{{ pending.length }}</b><span>UNDER REVIEW</span></div>
      <div class="card"><b>{{ approved.length }}</b><span>APPROVED</span></div>
    </div>

    <PipelinePanel />

    <AssignArticle @assigned="load" />

    <FilterBar
      :statuses="['ASSIGNED','DRAFTING','UNDER_REVIEW','REVISION_REQUESTED',
                   'APPROVED','PUBLISHED','WITHDRAWN']"
      @change="applyFilters" />

    <p v-if="!assigned.length" class="empty">No open assignments.</p>
    <ul v-else class="assigned">
      <li v-for="a in assigned" :key="a.id">
        <div class="meta">
          <span class="t">{{ a.title }}</span>
          <em>{{ a.writer_name }} · {{ a.status === 'ASSIGNED' ? 'not started' : 'drafting' }}</em>
        </div>
        <span v-if="a.deadline" class="due" :class="{ over: a.is_overdue }">
          {{ a.is_overdue ? 'Overdue' : `Due in ${a.days_to_deadline}d` }}
        </span>
      </li>
    </ul>

    <h3>Pending reviews</h3>
    <p v-if="loading">Loading…</p>
    <p v-else-if="!pending.length" class="empty">Nothing waiting for review.</p>
    <ul v-else>
      <li v-for="a in pending" :key="a.id" @click="router.push(`/editor/review/${a.id}`)">
        <div class="meta">
          <span class="t">{{ a.title }}</span>
          <em>Submitted by {{ a.writer_name }}</em>
        </div>
        <div class="score" :class="scoreClass(a.latest_score)">
          <b>{{ a.latest_score ?? '—' }}</b><small>score</small>
        </div>
      </li>
    </ul>

    <h3>Approved — assign to an issue</h3>
    <p class="note">
      Approved articles waiting to be assigned. Unassigned articles publish
      on their own; assigned ones publish with their issue.
    </p>
    <p v-if="!approved.length" class="empty">None.</p>
    <ul v-else>
      <li v-for="a in approved" :key="a.id" @click="router.push(`/editor/review/${a.id}`)">
        <div class="meta">
          <span class="t">{{ a.title }}</span>
          <em>{{ a.writer_name }} · {{ a.issue ? 'assigned to an issue' : 'not assigned' }}</em>
        </div>
        <span class="chip" :class="a.issue ? 'on' : 'off'">
          {{ a.issue ? 'In issue' : 'Standalone' }}
        </span>
      </li>
    </ul>

    <h3>Returned by pre-screening</h3>
    <p class="note">
      These scored below the passing mark of 70 and went back to their writer automatically.
      You can still open and approve them.
    </p>
    <p v-if="!returned.length" class="empty">None.</p>
    <ul v-else>
      <li v-for="a in returned" :key="a.id" @click="router.push(`/editor/review/${a.id}`)">
        <div class="meta">
          <span class="t">{{ a.title }}</span>
          <em>{{ a.writer_name }} · awaiting the writer's revision</em>
        </div>
        <div class="score bad"><b>{{ a.latest_score ?? '—' }}</b><small>score</small></div>
      </li>
    </ul>

    <DesignReview />
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
h3 { margin: 28px 0 6px; font-size: 15px; }
.note { margin: 0 0 10px; font-size: 12px; color: #888; line-height: 1.5; }
ul { list-style: none; padding: 0; margin: 0; }
li { display: flex; justify-content: space-between; align-items: center; gap: 14px;
     border: 1px solid #eee; border-radius: 8px; padding: 12px 14px;
     margin-bottom: 8px; cursor: pointer; }
li:hover { background: #fafafa; }
.meta { display: flex; flex-direction: column; gap: 3px; }
.t { font-weight: 600; }
em { font-size: 12px; color: #888; font-style: normal; }
.score { width: 52px; height: 52px; border-radius: 50%; border: 3px solid #ddd;
         display: flex; flex-direction: column; align-items: center; justify-content: center; flex-shrink: 0; }
.score b { font-size: 17px; line-height: 1; }
.score small { font-size: 9px; opacity: .65; }
.score.good { border-color: #2e9e63; color: #1c6b45; }
.score.bad { border-color: #c95757; color: #a33; }
.score.none { border-color: #ddd; color: #999; }
.assigned li { display: flex; justify-content: space-between; align-items: center;
               border: 1px solid #eee; border-radius: 8px; padding: 12px 14px;
               margin-bottom: 8px; }
.due { font-size: 11px; padding: 4px 10px; border-radius: 12px;
       background: #eef2f7; color: #445; }
.due.over { background: #fbe6e6; color: #a33; }
.chip { font-size: 11px; padding: 4px 10px; border-radius: 12px; }
.chip.on { background: #eaf1fb; color: #2b5a8f; }
.chip.off { background: #f2f2f2; color: #777; }
.empty { color: #888; font-size: 14px; }
</style>
