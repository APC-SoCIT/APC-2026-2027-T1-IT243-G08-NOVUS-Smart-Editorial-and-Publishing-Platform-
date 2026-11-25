<script setup>
/* All articles (adviser meeting, Nov 24): every article in one table, with
   who it is assigned to — or "Unassigned" for an open headline — its status,
   deadline and issue. Filters live in the address, so a view can be shared
   and the Back button returns to it. */
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../services/api'
import { useAuthStore } from '../stores/auth'
import { useCategories } from '../composables/useCategories'
import StaffLayout from '../components/StaffLayout.vue'
import SlideOver from '../components/SlideOver.vue'
import GiveToWriter from '../components/GiveToWriter.vue'
import UiBadge from '../components/ui/UiBadge.vue'
import UiEmpty from '../components/ui/UiEmpty.vue'
import UiSkeleton from '../components/ui/UiSkeleton.vue'
import UiCombobox from '../components/ui/UiCombobox.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const { load: loadCategories, optionsWith: categoryOptions } = useCategories()

/* One-click views, like saved filters in a ticketing system. */
const VIEWS = [
  { key: 'all', label: 'All' },
  { key: 'open', label: 'Open headlines', params: { status: 'OPEN' } },
  { key: 'writing', label: 'Being written',
    params: { status: 'ASSIGNED,DRAFTING,REVISION_REQUESTED' } },
  { key: 'review', label: 'In review',
    params: { status: 'AWAITING_EVALUATION,UNDER_REVIEW,PENDING_SIGNOFF' } },
  { key: 'overdue', label: 'Overdue', params: { overdue: 'true' } },
  { key: 'approved', label: 'Approved', params: { status: 'APPROVED' } },
  { key: 'published', label: 'Published', params: { status: 'PUBLISHED' } },
]

const COLUMNS = [
  { key: 'title', label: 'Headline' },
  { key: 'category', label: 'Category' },
  { key: 'writer', label: 'Writer' },
  { key: 'status', label: 'Status' },
  { key: 'deadline', label: 'Deadline' },
  { key: 'issue', label: 'Issue' },
  { key: 'updated_at', label: 'Updated' },
]

const q = (k, d = '') => (typeof route.query[k] === 'string' ? route.query[k] : d)
const view = ref(q('view', 'all'))
const search = ref(q('q'))
const category = ref(q('category'))
const writer = ref(q('writer'))
const issue = ref(q('issue'))
const sort = ref(q('sort', '-updated_at'))
const page = ref(Number(q('page', '1')) || 1)

const rows = ref([])
const count = ref(0)
const loading = ref(true)
const error = ref('')
const facets = ref({ writers: [], issues: [], has_unassigned: false })
const giving = ref(null)

const canAssign = computed(() => ['EDITOR', 'ADMIN'].includes(auth.role))
/* Filter choices come from the articles this user can see (facets), so
   the publisher gets them too without the staff directory. */
const writerOptions = computed(() => [
  ...(facets.value.has_unassigned ? [{ value: 'none', label: 'Unassigned', hint: 'open headlines' }] : []),
  ...facets.value.writers.map((w) => ({ value: String(w.id), label: w.name })),
])
const issueOptions = computed(() => [
  { value: 'none', label: 'Not in an issue' },
  ...facets.value.issues.map((i) => ({ value: String(i.id), label: `Issue ${i.number} — ${i.title}` })),
])
const pages = computed(() => Math.max(1, Math.ceil(count.value / 20)))
const range = computed(() => {
  if (!count.value) return '0'
  const from = (page.value - 1) * 20 + 1
  return `${from}–${Math.min(page.value * 20, count.value)} of ${count.value}`
})

async function load() {
  loading.value = true
  error.value = ''
  const preset = VIEWS.find((v) => v.key === view.value)?.params || {}
  const params = { ...preset, sort: sort.value, page: page.value }
  if (search.value.trim()) params.q = search.value.trim()
  if (category.value) params.category = category.value
  if (writer.value) params.writer = writer.value
  if (issue.value) params.issue = issue.value
  try {
    const { data } = await api.get('/editorial/articles/', { params })
    rows.value = data.results ?? data
    count.value = data.count ?? rows.value.length
  } catch (e) {
    // A page beyond the end after a filter change: go back to the first.
    if (e.response?.status === 404 && page.value > 1) { page.value = 1; return }
    error.value = 'Could not load the articles.'
  } finally { loading.value = false }
}

/* Keep the address in step with the filters, then fetch. */
function sync() {
  const query = {}
  if (view.value !== 'all') query.view = view.value
  if (search.value.trim()) query.q = search.value.trim()
  if (category.value) query.category = category.value
  if (writer.value) query.writer = writer.value
  if (issue.value) query.issue = issue.value
  if (sort.value !== '-updated_at') query.sort = sort.value
  if (page.value > 1) query.page = String(page.value)
  router.replace({ query })
  load()
}

/* A filter change starts again from page 1; changing the page fetches. */
const restart = () => (page.value === 1 ? sync() : (page.value = 1))
let typing = null
watch(search, () => { clearTimeout(typing); typing = setTimeout(restart, 300) })
watch([view, category, writer, issue, sort], restart)
watch(page, sync)

onMounted(async () => {
  loadCategories()
  load()
  try { facets.value = (await api.get('/editorial/articles/facets/')).data } catch { /* filters stay empty */ }
})

function sortBy(key) {
  sort.value = sort.value === key ? `-${key}` : key
}
const ariaSort = (key) =>
  sort.value === key ? 'ascending' : sort.value === `-${key}` ? 'descending' : 'none'
const arrow = (key) => (sort.value === key ? '↑' : sort.value === `-${key}` ? '↓' : '')

function openRow(a) {
  if (a.status === 'OPEN') {
    if (canAssign.value) giving.value = a
    return
  }
  router.push(`/editor/review/${a.id}`)
}

function clearFilters() {
  search.value = ''; category.value = ''; writer.value = ''; issue.value = ''; view.value = 'all'
}
const filtered = computed(() =>
  view.value !== 'all' || search.value || category.value || writer.value || issue.value)

const fmt = (d) => (d ? new Date(d).toLocaleDateString('en-PH', { month: 'short', day: 'numeric' }) : '—')
</script>

<template>
  <StaffLayout title="All articles"
               subtitle="Every article, who it is with, and where it stands">
    <nav class="views" aria-label="Saved views">
      <button v-for="v in VIEWS" :key="v.key" :class="{ on: view === v.key }"
              :aria-pressed="view === v.key" @click="view = v.key">{{ v.label }}</button>
    </nav>

    <div class="filters">
      <input v-model="search" type="search" class="search" aria-label="Search articles"
             placeholder="Search headline, writer or category" />
      <div class="pick">
        <UiCombobox v-model="category" :options="categoryOptions()" empty-label="All categories"
                    placeholder="Category" aria-label="Filter by category" />
      </div>
      <div class="pick">
        <UiCombobox v-model="writer" :options="writerOptions" empty-label="Any writer"
                    placeholder="Writer" aria-label="Filter by writer" />
      </div>
      <div class="pick">
        <UiCombobox v-model="issue" :options="issueOptions" empty-label="Any issue"
                    placeholder="Issue" aria-label="Filter by issue" />
      </div>
      <button v-if="filtered" class="clear" @click="clearFilters">Clear filters</button>
    </div>

    <p class="sr-only" role="status">{{ loading ? '' : `${count} articles` }}</p>
    <p v-if="error" class="err" role="alert">{{ error }}</p>
    <UiSkeleton v-else-if="loading && !rows.length" :rows="6" label="Loading articles" />
    <UiEmpty v-else-if="!rows.length" icon="○" title="No articles match"
             :body="filtered ? 'Try another view, or clear the filters.' : 'Assign an article to start the list.'" />

    <template v-else>
      <div class="tablewrap" :class="{ dim: loading }">
        <table>
          <caption class="sr-only">Articles, {{ range }}</caption>
          <thead>
            <tr>
              <th v-for="c in COLUMNS" :key="c.key" scope="col" :aria-sort="ariaSort(c.key)">
                <button class="sort" @click="sortBy(c.key)">
                  {{ c.label }} <span aria-hidden="true">{{ arrow(c.key) }}</span>
                </button>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="a in rows" :key="a.id" tabindex="0" :class="{ late: a.is_overdue }"
                @click="openRow(a)" @keyup.enter="openRow(a)">
              <th scope="row" class="title">{{ a.title }}</th>
              <td>{{ a.category || '—' }}</td>
              <td class="writer" :class="{ none: !a.writer_name }">{{ a.writer_name || 'Unassigned' }}</td>
              <td><UiBadge :status="a.status">{{ a.status_label }}</UiBadge></td>
              <td :class="{ bad: a.is_overdue }">
                {{ fmt(a.deadline) }}<span v-if="a.is_overdue" class="sr-only"> (overdue)</span>
              </td>
              <td>{{ a.issue_label || '—' }}</td>
              <td class="muted">{{ fmt(a.updated_at) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="pager">
        <span>{{ range }}</span>
        <button :disabled="page <= 1" @click="page--">← Previous</button>
        <button :disabled="page >= pages" @click="page++">Next →</button>
      </div>
    </template>
  </StaffLayout>

  <SlideOver :open="!!giving" title="Open headline"
             subtitle="Give it to a writer, or drop it from the backlog."
             @close="giving = null">
    <GiveToWriter v-if="giving" :key="giving.id" :article="giving"
                  @done="() => { giving = null; load() }" />
  </SlideOver>
</template>

<style scoped>
.views { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: var(--s-4); }
.views button { border: 1px solid var(--nv-line-strong); background: var(--nv-surface);
                color: var(--nv-text-muted); border-radius: var(--r-full);
                padding: 7px 14px; font-size: 14px; cursor: pointer; }
.views button.on { background: var(--nv-navy-2); border-color: var(--nv-navy-2);
                   color: #fff; font-weight: 600; }
.filters { display: flex; flex-wrap: wrap; gap: var(--s-3); align-items: center;
           margin-bottom: var(--s-5); }
.search { flex: 1 1 260px; padding: 10px 14px; font-size: 14px; font-family: inherit;
          border: 1px solid var(--nv-line-strong); border-radius: var(--r-sm);
          background: var(--nv-surface); color: var(--nv-text); }
.pick { width: 200px; }
.pick :deep(.cb) { margin-top: 0; }
.clear { background: none; border: 0; color: var(--nv-accent); cursor: pointer;
         font-size: 14px; text-decoration: underline; }

.tablewrap { overflow-x: auto; border: 1px solid var(--nv-line); border-radius: var(--r-md);
             background: var(--nv-surface); transition: opacity .15s; }
.tablewrap.dim { opacity: .6; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
thead th { position: sticky; top: 0; background: var(--nv-bg); text-align: left;
           border-bottom: 1px solid var(--nv-line); padding: 0; white-space: nowrap; }
.sort { width: 100%; text-align: left; background: none; border: 0; cursor: pointer;
        padding: 11px 14px; font-size: 12px; font-weight: 700; letter-spacing: .04em;
        text-transform: uppercase; color: var(--nv-text-muted); font-family: inherit; }
.sort:hover { color: var(--nv-text); }
tbody tr { cursor: pointer; border-bottom: 1px solid var(--nv-line); }
tbody tr:last-child { border-bottom: 0; }
tbody tr:hover, tbody tr:focus { background: var(--nv-accent-soft); outline: none; }
tbody tr.late { box-shadow: inset 3px 0 0 var(--bad); }
td, tbody th { padding: 12px 14px; color: var(--nv-text); vertical-align: middle; }
tbody th.title { font-weight: 600; text-align: left; min-width: 240px; }
td.writer { white-space: nowrap; }
td.none { color: var(--nv-text-faint); font-style: italic; }
td.bad { color: var(--bad); font-weight: 600; }
td.muted { color: var(--nv-text-muted); white-space: nowrap; }
.pager { display: flex; align-items: center; gap: var(--s-3); justify-content: flex-end;
         margin-top: var(--s-4); font-size: 14px; color: var(--nv-text-muted); }
.pager span { margin-right: auto; }
.pager button { border: 1px solid var(--nv-line-strong); background: var(--nv-surface);
                color: var(--nv-text); border-radius: var(--r-sm); padding: 7px 14px;
                cursor: pointer; font-size: 14px; }
.pager button:disabled { opacity: .45; cursor: not-allowed; }
.err { color: var(--bad); }
</style>
