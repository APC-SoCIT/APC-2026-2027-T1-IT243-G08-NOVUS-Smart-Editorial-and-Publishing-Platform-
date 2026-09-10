<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import api from '../services/api'
import { useAuthStore } from '../stores/auth'
import StaffLayout from '../components/StaffLayout.vue'
import AssignArticle from '../components/AssignArticle.vue'
import SlideOver from '../components/SlideOver.vue'
import DesignReview from '../components/DesignReview.vue'
import UiBadge from '../components/ui/UiBadge.vue'
import UiEmpty from '../components/ui/UiEmpty.vue'
import UiSkeleton from '../components/ui/UiSkeleton.vue'
import UiButton from '../components/ui/UiButton.vue'

const auth = useAuthStore()
const router = useRouter()

const articles = ref([])
const pipeline = ref(null)
const loading = ref(true)
const tab = ref('attention')
const search = ref('')
const assignOpen = ref(false)

const match = (a) => {
  const q = search.value.trim().toLowerCase()
  if (!q) return true
  return (a.title + ' ' + (a.writer_name || '')).toLowerCase().includes(q)
}

/* "Needs you" merges the review queue and gate returns: both are articles
   sitting still until an editor acts. Splitting them made the editor check
   two places for the same kind of work. */
const attention = computed(() => articles.value.filter(a =>
  (a.status === 'UNDER_REVIEW' || a.returned_by_ai) && match(a)))
const working = computed(() => articles.value.filter(a =>
  ['ASSIGNED', 'DRAFTING'].includes(a.status) && match(a)))
const approved = computed(() => articles.value.filter(a =>
  a.status === 'APPROVED' && match(a)))

const TABS = computed(() => [
  { key: 'attention', label: 'Needs you',   count: attention.value.length },
  { key: 'working',   label: 'Being written', count: working.value.length },
  { key: 'approved',  label: 'Approved',    count: approved.value.length },
  { key: 'layouts',   label: 'Layouts',     count: null },
])

const current = computed(() => ({
  attention: attention.value, working: working.value, approved: approved.value,
}[tab.value] || []))

async function load() {
  const [a, p] = await Promise.all([
    api.get('/editorial/articles/'),
    api.get('/editorial/articles/pipeline/'),
  ])
  articles.value = a.data.results ?? a.data
  pipeline.value = p.data
}

onMounted(async () => {
  try {
    if (!auth.user) await auth.fetchUser()
    await load()
  } finally { loading.value = false }
})

const open = (a) => router.push(`/editor/review/${a.id}`)
const initials = (n) => (n || '?').split(' ').map(p => p[0]).slice(0, 2).join('').toUpperCase()

const EMPTY = {
  attention: { icon: '✓', title: 'Nothing needs you',
    body: 'Submissions arrive here once they have been pre-screened.' },
  working: { icon: '○', title: 'Nothing being written',
    body: 'Assign a topic and it will appear here until the writer submits it.' },
  approved: { icon: '□', title: 'Nothing approved yet',
    body: 'Approved articles wait here until you assign them to an issue.' },
}
</script>

<template>
  <StaffLayout title="Editor dashboard" subtitle="What needs your attention today">

    <template #action>
      <UiButton variant="primary" @click="assignOpen = true">
        + Assign article
      </UiButton>
    </template>


    <!-- Alert first, and only when it matters. -->
    <div v-if="pipeline?.overdue" class="alert" role="status">
      <b>{{ pipeline.overdue }}
        {{ pipeline.overdue === 1 ? 'article is' : 'articles are' }} overdue.</b>
      <span v-if="pipeline.overdue_articles?.length">
        Latest: {{ pipeline.overdue_articles[0].title }}
        ({{ Math.abs(pipeline.overdue_articles[0].days_to_deadline) }} days late)
      </span>
      <button class="alink" @click="tab = 'working'">Show me</button>
    </div>

    <div class="toolbar">
      <nav class="tabs" role="tablist" aria-label="Article groups">
        <button v-for="t in TABS" :key="t.key" role="tab"
                :aria-selected="tab === t.key" :class="{ on: tab === t.key }"
                @click="tab = t.key">
          {{ t.label }}
          <span v-if="t.count !== null" class="count">{{ t.count }}</span>
        </button>
      </nav>

      <input v-if="tab !== 'layouts'" v-model="search" type="search"
             class="search" aria-label="Search articles"
             placeholder="Search by title or writer" />
    </div>

    <DesignReview v-if="tab === 'layouts'" />

    <template v-else>
      <UiSkeleton v-if="loading" :rows="4" label="Loading articles" />

      <UiEmpty v-else-if="!current.length" v-bind="EMPTY[tab]" />

      <ul v-else class="rows">
        <li v-for="a in current" :key="a.id" class="row" tabindex="0"
            role="button" @click="open(a)" @keyup.enter="open(a)">
          <span class="who" aria-hidden="true">{{ initials(a.writer_name) }}</span>

          <div class="meta">
            <span class="t">{{ a.title }}</span>
            <span class="sub">
              {{ a.writer_name }}
              <template v-if="a.category"> · {{ a.category }}</template>
              <template v-if="a.deadline && tab === 'working'">
                · <span :class="{ late: a.is_overdue }">
                    {{ a.is_overdue ? `${Math.abs(a.days_to_deadline)} days late`
                                    : `due in ${a.days_to_deadline} days` }}
                  </span>
              </template>
            </span>
          </div>

          <UiBadge v-if="a.returned_by_ai" tone="warn">Returned</UiBadge>
          <UiBadge v-else-if="tab === 'approved'"
                   :tone="a.issue ? 'info' : 'neutral'">
            {{ a.issue ? 'In an issue' : 'Standalone' }}
          </UiBadge>

          <span v-if="a.latest_score !== null && a.latest_score !== undefined"
                class="score" :class="a.latest_score >= 70 ? 'good' : 'bad'"
                :aria-label="`Pre-screening score ${a.latest_score}`">
            {{ a.latest_score }}
          </span>
        </li>
      </ul>
    </template>

    <!-- ---- rail: counts only ---- -->
    <template #rail>
      <div class="glance">
        <h2>At a glance</h2>
        <dl>
          <div><dt>Being written</dt><dd>{{ pipeline?.open ?? '–' }}</dd></div>
          <div :class="{ warn: pipeline?.due_soon }">
            <dt>Due within 2 days</dt><dd>{{ pipeline?.due_soon ?? '–' }}</dd>
          </div>
          <div :class="{ bad: pipeline?.overdue }">
            <dt>Overdue</dt><dd>{{ pipeline?.overdue ?? '–' }}</dd>
          </div>
          <div><dt>Awaiting an issue</dt>
               <dd>{{ pipeline?.unassigned_to_issue ?? '–' }}</dd></div>
        </dl>
      </div>

    </template>
  </StaffLayout>

  <SlideOver :open="assignOpen" title="Assign an article"
             subtitle="Give a writer a topic, an angle, and a deadline."
             @close="assignOpen = false">
    <AssignArticle @assigned="() => { assignOpen = false; load() }" />
  </SlideOver>
</template>

<style scoped>
/* ---- alert ---- */
.alert { display: flex; align-items: center; gap: var(--s-3); flex-wrap: wrap;
         background: var(--bad-bg); border: 1px solid var(--bad-line);
         border-radius: var(--r-md); padding: var(--s-4) var(--s-5);
         margin-bottom: var(--s-5); font-size: 15px; color: var(--bad); }
.alert b { font-weight: 700; }
.alert span { color: #7a3a3a; }
.alink { margin-left: auto; background: var(--bad); color: #fff; border: 0;
         border-radius: var(--r-sm); padding: 7px 16px; font-size: 14px;
         font-weight: 600; cursor: pointer; }

/* ---- toolbar ---- */
.toolbar { display: flex; align-items: center; gap: var(--s-4);
           margin-bottom: var(--s-5); flex-wrap: wrap; }
.tabs { display: flex; gap: var(--s-1); flex: 1; }
.tabs button { display: inline-flex; align-items: center; gap: 8px;
               background: none; border: 0; border-radius: var(--r-sm);
               padding: 10px 16px; font-size: 15px; font-weight: 500;
               color: var(--nv-text-muted); cursor: pointer;
               transition: background var(--dur-fast) var(--ease-out),
                           color var(--dur-fast) var(--ease-out); }
.tabs button:hover { background: #eef0f3; color: var(--nv-text); }
.tabs button.on { background: var(--nv-navy-2); color: #fff; font-weight: 600; }
.count { font-size: 13px; font-weight: 700; padding: 1px 8px;
         border-radius: var(--r-full); background: #e4e7ec; color: var(--nv-text-muted); }
.tabs button.on .count { background: rgba(255,255,255,.22); color: #fff; }

.search { width: 260px; padding: 10px 14px; font-size: 15px;
          border: 1px solid var(--nv-line-strong); border-radius: var(--r-sm);
          font-family: inherit; background: var(--nv-surface); }

/* ---- rows ---- */
.rows { list-style: none; margin: 0; padding: 0;
        display: flex; flex-direction: column; gap: 8px; }
.row { display: flex; align-items: center; gap: var(--s-4);
       padding: 14px 18px; background: var(--nv-surface);
       border: 1px solid var(--nv-line); border-radius: var(--r-md);
       cursor: pointer;
       transition: border-color var(--dur-fast) var(--ease-out),
                   box-shadow var(--dur-fast) var(--ease-out); }
.row:hover { border-color: var(--nv-line-strong); box-shadow: var(--shadow-sm); }

.who { width: 36px; height: 36px; border-radius: 50%; flex-shrink: 0;
       background: var(--nv-navy-2); color: #fff;
       display: flex; align-items: center; justify-content: center;
       font-size: 12px; font-weight: 700; }

.meta { flex: 1; min-width: 0; }
.t { display: block; font-size: 16px; font-weight: 600; color: var(--nv-text);
     line-height: 1.35; margin-bottom: 3px;
     overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sub { font-size: 14px; color: var(--nv-text-muted); }
.late { color: var(--bad); font-weight: 600; }

.score { min-width: 42px; padding: 5px 10px; border-radius: var(--r-sm);
         text-align: center; font-size: 15px; font-weight: 700;
         font-variant-numeric: tabular-nums; border: 1px solid; flex-shrink: 0; }
.score.good { border-color: var(--ok-line);  color: var(--ok);  background: var(--ok-bg); }
.score.bad  { border-color: var(--bad-line); color: var(--bad); background: var(--bad-bg); }

/* ---- rail ---- */
.glance { background: var(--nv-surface); border: 1px solid var(--nv-line);
          border-radius: var(--r-md); padding: var(--s-5); }
.glance h2 { font-size: 13px; letter-spacing: .06em; text-transform: uppercase;
             color: var(--nv-text-faint); margin: 0 0 var(--s-4); font-weight: 600; }
dl { margin: 0; }
dl > div { display: flex; justify-content: space-between; align-items: baseline;
           padding: 10px 0; border-bottom: 1px solid var(--nv-line); }
dl > div:last-child { border-bottom: 0; }
dt { font-size: 14px; color: var(--nv-text-muted); }
dd { margin: 0; font-size: 20px; font-weight: 700; color: var(--nv-text);
     font-variant-numeric: tabular-nums; }
dl > div.warn dd { color: var(--warn); }
dl > div.bad dd { color: var(--bad); }

@media (max-width: 780px) {
  .toolbar { flex-direction: column; align-items: stretch; }
  .search { width: 100%; }
}
</style>
