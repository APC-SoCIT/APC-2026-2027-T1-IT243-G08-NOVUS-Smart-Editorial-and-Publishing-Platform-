<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import api from '../services/api'
import { useAuthStore } from '../stores/auth'
import StaffLayout from '../components/StaffLayout.vue'
import RailPanel from '../components/RailPanel.vue'
import AssignArticle from '../components/AssignArticle.vue'
import DesignReview from '../components/DesignReview.vue'
import FilterBar from '../components/FilterBar.vue'
import UiTabs from '../components/ui/UiTabs.vue'
import UiBadge from '../components/ui/UiBadge.vue'
import UiEmpty from '../components/ui/UiEmpty.vue'
import UiSkeleton from '../components/ui/UiSkeleton.vue'
import UiButton from '../components/ui/UiButton.vue'

const auth = useAuthStore()
const router = useRouter()

const articles = ref([])
const pipeline = ref(null)
const loading = ref(true)
const filters = ref({})
const tab = ref('review')
const showAssign = ref(false)

const by = (fn) => computed(() => articles.value.filter(fn))

const pending  = by(a => a.status === 'UNDER_REVIEW')
const inProg   = by(a => ['ASSIGNED', 'DRAFTING'].includes(a.status))
const approved = by(a => a.status === 'APPROVED')
const returned = by(a => a.returned_by_ai)

const TABS = computed(() => [
  { key: 'review',   label: 'Waiting for you', count: pending.value.length },
  { key: 'progress', label: 'In progress',     count: inProg.value.length },
  { key: 'approved', label: 'Approved',        count: approved.value.length },
  { key: 'returned', label: 'Returned',        count: returned.value.length, alert: true },
  { key: 'layouts',  label: 'Layouts' },
])

const current = computed(() => ({
  review: pending.value, progress: inProg.value,
  approved: approved.value, returned: returned.value,
}[tab.value] || []))

async function load() {
  const [a, p] = await Promise.all([
    api.get('/editorial/articles/', { params: filters.value }),
    api.get('/editorial/articles/pipeline/'),
  ])
  articles.value = a.data.results ?? a.data
  pipeline.value = p.data
}

function applyFilters(f) { filters.value = f; load() }

onMounted(async () => {
  try {
    if (!auth.user) await auth.fetchUser()
    await load()
  } finally { loading.value = false }
})

const open = (a) => router.push(`/editor/review/${a.id}`)

const initials = (name) => (name || '?')
  .split(' ').map(p => p[0]).slice(0, 2).join('').toUpperCase()
const scoreTone = (s) => s === null ? 'none' : s >= 70 ? 'good' : 'bad'

const EMPTY = {
  review:   { icon: '✓', title: 'Nothing waiting',
              body: 'Submissions that clear the pre-screening gate arrive here with their score.' },
  progress: { icon: '○', title: 'No open assignments',
              body: 'Assign a topic and it stays here until the writer submits it.' },
  approved: { icon: '□', title: 'Nothing approved yet',
              body: 'Approved articles wait here until you assign them to an issue.' },
  returned: { icon: '↩', title: 'None returned',
              body: 'Submissions scoring below the threshold appear here as well as going back to their writer.' },
}
</script>

<template>
  <StaffLayout title="Editor dashboard" subtitle="Assignments, reviews, and layouts">

    <!-- ============ MAIN ============ -->
    <UiTabs v-model="tab" :tabs="TABS" />

    <template v-if="tab === 'layouts'">
      <DesignReview />
    </template>

    <template v-else>
      <FilterBar
        :statuses="['ASSIGNED','DRAFTING','UNDER_REVIEW','REVISION_REQUESTED',
                    'APPROVED','PUBLISHED','WITHDRAWN']"
        @change="applyFilters" />

      <UiSkeleton v-if="loading" :rows="4" label="Loading the editorial pipeline" />

      <UiEmpty v-else-if="!current.length" v-bind="EMPTY[tab]">
        <template v-if="tab === 'progress'" #action>
          <UiButton variant="primary" @click="showAssign = true">
            Assign an article
          </UiButton>
        </template>
      </UiEmpty>

      <ul v-else class="rows">
        <li v-for="a in current" :key="a.id" class="row" tabindex="0"
            role="button" @click="open(a)" @keyup.enter="open(a)">
          <span class="spine" :data-cat="a.category" aria-hidden="true"></span>
          <span class="who" aria-hidden="true">{{ initials(a.writer_name) }}</span>
          <div class="meta">
            <span class="t">{{ a.title }}</span>
            <span class="sub">
              {{ a.writer_name }}
              <template v-if="a.category"> · {{ a.category }}</template>
            </span>
          </div>

          <div class="trail">
            <UiBadge v-if="tab === 'approved'" :tone="a.issue ? 'info' : 'neutral'">
              {{ a.issue ? 'In an issue' : 'Standalone' }}
            </UiBadge>
            <UiBadge v-else-if="tab === 'progress'" :status="a.status" dot />

            <span v-if="a.deadline && tab === 'progress'"
                  class="due" :class="{ over: a.is_overdue }">
              {{ a.is_overdue ? `${Math.abs(a.days_to_deadline)}d late`
                              : `${a.days_to_deadline}d left` }}
            </span>

            <span v-if="['review','returned'].includes(tab)"
                  class="score" :class="scoreTone(a.latest_score)"
                  :aria-label="`Pre-screening score ${a.latest_score ?? 'unavailable'}`">
              {{ a.latest_score ?? '—' }}
            </span>
          </div>
        </li>
      </ul>
    </template>

    <!-- ============ RAIL ============ -->
    <template #rail>
      <RailPanel title="Pipeline">
        <div v-if="pipeline" class="stats">
          <div class="stat">
            <b>{{ pipeline.open }}</b><span>In progress</span>
          </div>
          <div class="stat" :class="{ warn: pipeline.due_soon }">
            <b>{{ pipeline.due_soon }}</b><span>Due soon</span>
          </div>
          <div class="stat" :class="{ bad: pipeline.overdue }">
            <b>{{ pipeline.overdue }}</b><span>Overdue</span>
          </div>
          <div class="stat">
            <b>{{ pipeline.unassigned_to_issue }}</b><span>Unassigned</span>
          </div>
        </div>
      </RailPanel>

      <RailPanel title="Quick actions">
        <UiButton variant="primary" full @click="showAssign = true">
          + Assign article
        </UiButton>
        <UiButton variant="ghost" full class="mt"
                  @click="router.push('/reports')">
          View reports
        </UiButton>
      </RailPanel>

      <RailPanel v-if="pipeline?.overdue_articles?.length" title="Needs chasing">
        <ul class="mini">
          <li v-for="a in pipeline.overdue_articles.slice(0, 5)" :key="a.id"
              @click="open(a)" tabindex="0" role="button" @keyup.enter="open(a)">
            <span class="mt-t">{{ a.title }}</span>
            <span class="mt-s">
              {{ a.writer_name }} · {{ Math.abs(a.days_to_deadline) }}d late
            </span>
          </li>
        </ul>
      </RailPanel>

      <RailPanel v-if="pipeline?.workload?.length" title="Writer workload">
        <ul class="load">
          <li v-for="w in pipeline.workload.slice(0, 6)" :key="w.writer">
            <span class="name">{{ w.writer }}</span>
            <span class="bars" aria-hidden="true">
              <i v-for="n in Math.min(w.open, 8)" :key="n"
                 :class="{ late: n <= w.overdue }"></i>
            </span>
            <span class="n">{{ w.open }}</span>
          </li>
        </ul>
      </RailPanel>
    </template>
  </StaffLayout>

  <!-- assignment form, opened from the rail -->
  <div v-if="showAssign" class="modal" @click.self="showAssign = false">
    <div class="mbox">
      <AssignArticle @assigned="() => { showAssign = false; load() }" />
      <UiButton variant="quiet" full @click="showAssign = false">Close</UiButton>
    </div>
  </div>
</template>

<style scoped>
.rows { list-style: none; margin: 0; padding: 0;
        display: flex; flex-direction: column; gap: 6px; }

/* A fixed grid rather than flex-grow: the meta column takes the slack, so the
   trailing badge or score sits at a predictable distance instead of drifting
   to the far edge of an empty row. */
.row { display: grid;
       grid-template-columns: 3px 30px minmax(0, 1fr) auto;
       align-items: center; gap: var(--s-3);
       padding: 10px var(--s-4) 10px 0;
       background: var(--nv-surface); border: 1px solid var(--nv-line);
       border-radius: var(--r-sm); cursor: pointer; overflow: hidden;
       transition: border-color var(--dur-fast) var(--ease-out),
                   box-shadow var(--dur-fast) var(--ease-out); }
.row:hover { border-color: var(--nv-line-strong); box-shadow: var(--shadow-sm); }

/* Category colour rail — gives the eye a track to follow down the list. */
.spine { width: 3px; height: 100%; background: var(--nv-line-strong);
         align-self: stretch; }
.spine[data-cat="Business"]   { background: #4a7fb5; }
.spine[data-cat="Tech"]       { background: #1c6b45; }
.spine[data-cat="Life"]       { background: #b5651d; }
.spine[data-cat="Innovation"] { background: #6b4a9e; }
.spine[data-cat="Leadership"] { background: #2b5a8f; }

.who { width: 30px; height: 30px; border-radius: 50%; background: var(--nv-bg);
       border: 1px solid var(--nv-line); color: var(--nv-text-muted);
       display: flex; align-items: center; justify-content: center;
       font-size: 10px; font-weight: 700; letter-spacing: .02em;
       margin-left: var(--s-3); }

.meta { min-width: 0; display: flex; flex-direction: column; gap: 1px; }

/* One cell for everything trailing, so the row never wraps to two lines
   however many indicators a given tab shows. */
.trail { display: flex; align-items: center; gap: var(--s-3);
         white-space: nowrap; }
.t { font-size: var(--t-sm); font-weight: 600; color: var(--nv-text);
     overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sub { font-size: var(--t-xs); color: var(--nv-text-muted); }

.due { font-size: var(--t-xs); color: var(--nv-text-muted); white-space: nowrap; }
.due.over { color: var(--bad); font-weight: 600; }

/* A pill in a list, not a ring. The ring belongs on the review screen where
   the score is the subject; here it only competes with the headline. */
.score { min-width: 34px; padding: 3px var(--s-2); border-radius: var(--r-sm);
         text-align: center; font-size: var(--t-sm); font-weight: 700;
         font-variant-numeric: tabular-nums; border: 1px solid; }
.score.good { border-color: var(--ok-line);  color: var(--ok);  background: var(--ok-bg); }
.score.bad  { border-color: var(--bad-line); color: var(--bad); background: var(--bad-bg); }
.score.none { border-color: var(--nv-line);  color: var(--nv-text-faint);
              background: var(--nv-bg); }

/* rail */
.stats { display: grid; grid-template-columns: 1fr 1fr; gap: var(--s-2); }
.stat { border: 1px solid var(--nv-line); border-radius: var(--r-sm);
        padding: var(--s-3); text-align: center; }
.stat b { display: block; font-size: var(--t-lg); color: var(--nv-text); }
.stat span { font-size: var(--t-xs); color: var(--nv-text-muted); }
.stat.warn { background: var(--warn-bg); border-color: var(--warn-line); }
.stat.warn b { color: var(--warn); }
.stat.bad { background: var(--bad-bg); border-color: var(--bad-line); }
.stat.bad b { color: var(--bad); }
.mt { margin-top: var(--s-2); }

.mini { list-style: none; margin: 0; padding: 0; }
.mini li { padding: var(--s-2) 0; border-bottom: 1px solid var(--nv-line);
           cursor: pointer; }
.mini li:last-child { border-bottom: 0; }
.mini li:hover .mt-t { color: var(--nv-accent); }
.mt-t { display: block; font-size: var(--t-sm); font-weight: 600;
        color: var(--nv-text); overflow: hidden; text-overflow: ellipsis;
        white-space: nowrap; }
.mt-s { font-size: var(--t-xs); color: var(--bad); }

.load { list-style: none; margin: 0; padding: 0; }
.load li { display: flex; align-items: center; gap: var(--s-2);
           padding: var(--s-2) 0; }
.name { flex: 1; font-size: var(--t-xs); color: var(--nv-text);
        overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.bars { display: flex; gap: 2px; }
.bars i { width: 5px; height: 14px; border-radius: 1px; background: #cddcee; }
.bars i.late { background: #d99; }
.load .n { font-size: var(--t-xs); color: var(--nv-text-faint); width: 16px;
           text-align: right; }

.modal { position: fixed; inset: 0; background: rgba(13,21,38,.55);
         display: flex; align-items: center; justify-content: center;
         z-index: 60; padding: var(--s-5); }
.mbox { background: var(--nv-surface); border-radius: var(--r-lg);
        padding: var(--s-5); width: 100%; max-width: 560px;
        max-height: 88vh; overflow-y: auto; box-shadow: var(--shadow-lg); }
</style>
