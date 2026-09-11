<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../services/api'
import { useAuthStore } from '../stores/auth'
import StaffLayout from '../components/StaffLayout.vue'
import UiBadge from '../components/ui/UiBadge.vue'
import UiEmpty from '../components/ui/UiEmpty.vue'
import UiSkeleton from '../components/ui/UiSkeleton.vue'
import UiButton from '../components/ui/UiButton.vue'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const articles = ref([])
const loading = ref(true)
const tab = ref('todo')
const search = ref('')
const justScored = ref(route.query.score ?? null)

const match = (a) => {
  const q = search.value.trim().toLowerCase()
  return !q || a.title.toLowerCase().includes(q)
}

/* "To write" merges new assignments, drafts in hand, and anything the editor
   or the gate sent back. All three are work sitting with the writer, and
   splitting them made it easy to miss a returned piece. */
const todo = computed(() => articles.value.filter(a =>
  ['ASSIGNED', 'DRAFTING', 'REVISION_REQUESTED'].includes(a.status) && match(a)))
const waiting = computed(() => articles.value.filter(a =>
  ['UNDER_REVIEW', 'AWAITING_EVALUATION'].includes(a.status) && match(a)))
const done = computed(() => articles.value.filter(a =>
  ['APPROVED', 'PUBLISHED'].includes(a.status) && match(a)))

const TABS = computed(() => [
  { key: 'todo',    label: 'To write',       count: todo.value.length },
  { key: 'waiting', label: 'With the editor', count: waiting.value.length },
  { key: 'done',    label: 'Finished',        count: done.value.length },
])

const current = computed(() => ({
  todo: todo.value, waiting: waiting.value, done: done.value,
}[tab.value] || []))

const overdue = computed(() => todo.value.filter(a => a.is_overdue))
const dueSoon = computed(() => todo.value.filter(a =>
  !a.is_overdue && a.days_to_deadline !== null && a.days_to_deadline <= 2))

async function load() {
  const { data } = await api.get('/editorial/articles/')
  articles.value = data.results ?? data
}

onMounted(async () => {
  try {
    if (!auth.user) await auth.fetchUser()
    await load()
  } finally { loading.value = false }
})

function open(a) {
  if (['ASSIGNED', 'DRAFTING', 'REVISION_REQUESTED'].includes(a.status)) {
    router.push(`/writer/compose/${a.id}`)
  }
}

const EMPTY = {
  todo: { icon: '○', title: 'Nothing to write',
    body: 'Assignments from your editor appear here, along with any article sent back for revision.' },
  waiting: { icon: '↑', title: 'Nothing with the editor',
    body: 'Articles you submit sit here while they are reviewed.' },
  done: { icon: '✓', title: 'Nothing finished yet',
    body: 'Approved and published articles collect here.' },
}
</script>

<template>
  <StaffLayout title="Writer dashboard"
               :subtitle="`Welcome back, ${auth.user?.first_name || ''}`">

    <template #action>
      <UiButton variant="primary" @click="router.push('/writer/compose')">
        + Draft article
      </UiButton>
    </template>

    <div v-if="justScored !== null" class="flash" role="status">
      <template v-if="Number(justScored) >= 70">
        <b>Submitted.</b> Pre-screening scored {{ justScored }} and your editor
        has it now.
      </template>
      <template v-else-if="Number(justScored) > 0">
        <b>Returned for revision.</b> Pre-screening scored {{ justScored }},
        below the passing mark of 70.
      </template>
      <template v-else>
        <b>Submitted.</b> Automated evaluation was unavailable, so your editor
        will review it without a score.
      </template>
      <button class="fx" aria-label="Dismiss" @click="justScored = null">×</button>
    </div>

    <div v-if="overdue.length" class="alert" role="status">
      <b>{{ overdue.length }}
        {{ overdue.length === 1 ? 'article is' : 'articles are' }} overdue.</b>
      <span>{{ overdue[0].title }} —
        {{ Math.abs(overdue[0].days_to_deadline) }} days late</span>
    </div>

    <div class="toolbar">
      <nav class="tabs" role="tablist" aria-label="Your articles">
        <button v-for="t in TABS" :key="t.key" role="tab"
                :aria-selected="tab === t.key" :class="{ on: tab === t.key }"
                @click="tab = t.key">
          {{ t.label }}<span class="count">{{ t.count }}</span>
        </button>
      </nav>
      <input v-model="search" type="search" class="search"
             aria-label="Search your articles" placeholder="Search your articles" />
    </div>

    <UiSkeleton v-if="loading" :rows="4" label="Loading your articles" />

    <UiEmpty v-else-if="!current.length" v-bind="EMPTY[tab]">
      <template v-if="tab === 'todo'" #action>
        <UiButton variant="primary" @click="router.push('/writer/compose')">
          Draft an article
        </UiButton>
      </template>
    </UiEmpty>

    <ul v-else class="rows">
      <li v-for="a in current" :key="a.id" class="row"
          :class="{ clickable: tab === 'todo' }"
          :tabindex="tab === 'todo' ? 0 : -1"
          :role="tab === 'todo' ? 'button' : undefined"
          @click="open(a)" @keyup.enter="open(a)">
        <div class="meta">
          <span class="t">{{ a.title }}</span>
          <span class="sub">
            {{ a.category || 'Uncategorised' }}
            <template v-if="a.deadline && tab === 'todo'">
              · <span :class="{ late: a.is_overdue }">
                  {{ a.is_overdue ? `${Math.abs(a.days_to_deadline)} days late`
                                  : `due in ${a.days_to_deadline} days` }}
                </span>
            </template>
          </span>
          <p v-if="a.brief && a.status === 'ASSIGNED'" class="brief">{{ a.brief }}</p>
        </div>

        <UiBadge v-if="a.returned_by_ai" tone="warn">Needs revision</UiBadge>
        <UiBadge v-else :status="a.status" dot />

        <span v-if="a.latest_score" class="score"
              :class="a.latest_score >= 70 ? 'good' : 'bad'"
              :aria-label="`Pre-screening score ${a.latest_score}`">
          {{ a.latest_score }}
        </span>
      </li>
    </ul>

    <template #rail>
      <div class="glance">
        <h2>At a glance</h2>
        <dl>
          <div><dt>To write</dt><dd>{{ todo.length }}</dd></div>
          <div :class="{ warn: dueSoon.length }">
            <dt>Due within 2 days</dt><dd>{{ dueSoon.length }}</dd>
          </div>
          <div :class="{ bad: overdue.length }">
            <dt>Overdue</dt><dd>{{ overdue.length }}</dd>
          </div>
          <div><dt>With the editor</dt><dd>{{ waiting.length }}</dd></div>
        </dl>
      </div>

      <div v-if="dueSoon.length || overdue.length" class="glance">
        <h2>Next deadlines</h2>
        <ul class="due">
          <li v-for="a in [...overdue, ...dueSoon].slice(0, 4)" :key="a.id"
              tabindex="0" role="button" @click="open(a)" @keyup.enter="open(a)">
            <span class="dt">{{ a.title }}</span>
            <span class="dd" :class="{ late: a.is_overdue }">
              {{ a.is_overdue ? `${Math.abs(a.days_to_deadline)}d late`
                              : `${a.days_to_deadline}d left` }}
            </span>
          </li>
        </ul>
      </div>
    </template>
  </StaffLayout>
</template>

<style scoped>
.flash { display: flex; align-items: center; gap: var(--s-3);
         background: var(--info-bg); border: 1px solid #cfe0f5;
         border-radius: var(--r-md); padding: var(--s-4) var(--s-5);
         margin-bottom: var(--s-4); font-size: 15px; color: var(--info); }
.fx { margin-left: auto; background: none; border: 0; font-size: 22px;
      line-height: 1; color: inherit; cursor: pointer; padding: 0 4px; }

.alert { display: flex; align-items: center; gap: var(--s-3); flex-wrap: wrap;
         background: var(--bad-bg); border: 1px solid var(--bad-line);
         border-radius: var(--r-md); padding: var(--s-4) var(--s-5);
         margin-bottom: var(--s-5); font-size: 15px; color: var(--bad); }
.alert span { color: #7a3a3a; }

.toolbar { display: flex; align-items: center; gap: var(--s-4);
           margin-bottom: var(--s-5); flex-wrap: wrap; }
.tabs { display: flex; gap: var(--s-1); flex: 1; }
.tabs button { display: inline-flex; align-items: center; gap: 8px;
               background: none; border: 0; border-radius: var(--r-sm);
               padding: 10px 16px; font-size: 15px; font-weight: 500;
               color: var(--nv-text-muted); cursor: pointer;
               transition: background var(--dur-fast) var(--ease-out); }
.tabs button:hover { background: #eef0f3; color: var(--nv-text); }
.tabs button.on { background: var(--nv-navy-2); color: #fff; font-weight: 600; }
.count { font-size: 13px; font-weight: 700; padding: 1px 8px;
         border-radius: var(--r-full); background: #e4e7ec; color: var(--nv-text-muted); }
.tabs button.on .count { background: rgba(255,255,255,.22); color: #fff; }
.search { width: 240px; padding: 10px 14px; font-size: 15px;
          border: 1px solid var(--nv-line-strong); border-radius: var(--r-sm);
          font-family: inherit; background: var(--nv-surface); }

.rows { list-style: none; margin: 0; padding: 0;
        display: flex; flex-direction: column; gap: 8px; }
.row { display: flex; align-items: flex-start; gap: var(--s-4);
       padding: 14px 18px; background: var(--nv-surface);
       border: 1px solid var(--nv-line); border-radius: var(--r-md); }
.row.clickable { cursor: pointer;
                 transition: border-color var(--dur-fast) var(--ease-out),
                             box-shadow var(--dur-fast) var(--ease-out); }
.row.clickable:hover { border-color: var(--nv-line-strong); box-shadow: var(--shadow-sm); }

.meta { flex: 1; min-width: 0; }
.t { display: block; font-size: 16px; font-weight: 600; color: var(--nv-text);
     line-height: 1.35; margin-bottom: 3px; }
.sub { font-size: 14px; color: var(--nv-text-muted); }
.late { color: var(--bad); font-weight: 600; }
.brief { margin: 8px 0 0; font-size: 14px; line-height: 1.55;
         color: var(--nv-text-muted); padding-left: 12px;
         border-left: 2px solid var(--nv-line-strong); }

.score { min-width: 42px; padding: 5px 10px; border-radius: var(--r-sm);
         text-align: center; font-size: 15px; font-weight: 700;
         font-variant-numeric: tabular-nums; border: 1px solid; flex-shrink: 0; }
.score.good { border-color: var(--ok-line);  color: var(--ok);  background: var(--ok-bg); }
.score.bad  { border-color: var(--bad-line); color: var(--bad); background: var(--bad-bg); }

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

.due { list-style: none; margin: 0; padding: 0; }
.due li { display: flex; justify-content: space-between; align-items: baseline;
          gap: var(--s-3); padding: 9px 0; border-bottom: 1px solid var(--nv-line);
          cursor: pointer; }
.due li:last-child { border-bottom: 0; }
.due li:hover .dt { color: var(--nv-accent); }
.dt { font-size: 14px; color: var(--nv-text); overflow: hidden;
      text-overflow: ellipsis; white-space: nowrap; }
.dd { font-size: 13px; color: var(--nv-text-muted); white-space: nowrap; }
.dd.late { color: var(--bad); font-weight: 600; }

@media (max-width: 780px) {
  .toolbar { flex-direction: column; align-items: stretch; }
  .search { width: 100%; }
}
</style>
