<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import api from '../services/api'
import StaffLayout from '../components/StaffLayout.vue'
import UiEmpty from '../components/ui/UiEmpty.vue'
import UiSkeleton from '../components/ui/UiSkeleton.vue'

const router = useRouter()

const articles = ref([])
const facets = ref({ years: [], categories: [], issues: [], total: 0 })
const loading = ref(true)
const count = ref(0)

const q = ref('')
const year = ref('')
const category = ref('')
const issue = ref('')

let debounce = null

async function load() {
  const { data } = await api.get('/editorial/articles/archive/', {
    params: {
      q: q.value || undefined,
      year: year.value || undefined,
      category: category.value || undefined,
      issue: issue.value || undefined,
    },
  })
  articles.value = data.results ?? data
  count.value = data.count ?? articles.value.length
  loading.value = false
}

function search() {
  clearTimeout(debounce)
  debounce = setTimeout(load, 300)
}

function clear() {
  q.value = ''; year.value = ''; category.value = ''; issue.value = ''
  load()
}

const filtered = computed(() =>
  Boolean(q.value || year.value || category.value || issue.value))

onMounted(async () => {
  const { data } = await api.get('/editorial/articles/archive-facets/')
  facets.value = data
  await load()
})

/* Grouped by month: a back catalogue is read chronologically, and a flat list
   of a hundred articles gives the eye nothing to hold on to. */
const grouped = computed(() => {
  const map = new Map()
  for (const a of articles.value) {
    const d = a.published_at ? new Date(a.published_at) : null
    const key = d
      ? d.toLocaleDateString('en-PH', { year: 'numeric', month: 'long' })
      : 'Date not recorded'
    if (!map.has(key)) map.set(key, [])
    map.get(key).push(a)
  }
  return [...map.entries()].map(([label, items]) => ({ label, items }))
})

const issueLabel = (a) => {
  if (!a.issue) return 'Standalone'
  const i = facets.value.issues.find(x => x.id === a.issue)
  return i ? `Issue ${i.number}` : `Issue #${a.issue}`
}

const day = (d) => d
  ? new Date(d).toLocaleDateString('en-PH', { day: 'numeric', month: 'short' })
  : '—'
</script>

<template>
  <StaffLayout title="Archive"
               subtitle="Everything BOSS Magazine PH has published">

    <div class="bar">
      <input v-model="q" type="search" class="search"
             aria-label="Search the archive"
             placeholder="Search headlines, copy, or writers…"
             @input="search" />

      <select v-model="issue" aria-label="Filter by issue" @change="load">
        <option value="">All issues</option>
        <option v-for="i in facets.issues" :key="i.id" :value="i.id">
          Issue {{ i.number }} — {{ i.title }}
        </option>
      </select>

      <select v-model="category" aria-label="Filter by category" @change="load">
        <option value="">All categories</option>
        <option v-for="c in facets.categories" :key="c" :value="c">{{ c }}</option>
      </select>

      <select v-model="year" aria-label="Filter by year" @change="load">
        <option value="">All years</option>
        <option v-for="y in facets.years" :key="y" :value="y">{{ y }}</option>
      </select>

      <button v-if="filtered" class="clear" @click="clear">Clear</button>
    </div>

    <p class="count" role="status">
      <template v-if="filtered">{{ count }} of {{ facets.total }} articles</template>
      <template v-else>{{ facets.total }} articles published</template>
    </p>

    <UiSkeleton v-if="loading" :rows="5" label="Loading the archive" />

    <UiEmpty v-else-if="!articles.length"
             :icon="filtered ? '⌕' : '▤'"
             :title="filtered ? 'Nothing matches that' : 'Nothing published yet'"
             :body="filtered
               ? 'Try a different search, or clear the filters to see everything.'
               : 'Published articles collect here, grouped by the month they ran.'" />

    <section v-else v-for="g in grouped" :key="g.label" class="month">
      <h2>{{ g.label }} <span>{{ g.items.length }}</span></h2>

      <ul class="rows">
        <li v-for="a in g.items" :key="a.id" class="row" tabindex="0" role="button"
            @click="router.push(`/editor/review/${a.id}`)"
            @keyup.enter="router.push(`/editor/review/${a.id}`)">
          <span class="date">{{ day(a.published_at) }}</span>

          <div class="meta">
            <span class="t">{{ a.title }}</span>
            <span class="sub">
              {{ a.writer_name }}
              <template v-if="a.category"> · {{ a.category }}</template>
              · {{ a.reading_time }} min read
            </span>
          </div>

          <span class="issue" :class="{ standalone: !a.issue }">
            {{ issueLabel(a) }}
          </span>
          <span v-if="a.is_premium" class="prem">Subscriber</span>
        </li>
      </ul>
    </section>
  </StaffLayout>
</template>

<style scoped>
.bar { display: flex; gap: var(--s-2); margin-bottom: var(--s-4); flex-wrap: wrap; }
.search { flex: 1; min-width: 240px; padding: 10px 14px; font-size: 15px;
          border: 1px solid var(--nv-line-strong); border-radius: var(--r-sm);
          font-family: inherit; background: var(--nv-surface); color: var(--nv-text); }
select { padding: 10px 12px; font-size: 14px; font-family: inherit;
         border: 1px solid var(--nv-line-strong); border-radius: var(--r-sm);
         background: var(--nv-surface); color: var(--nv-text); cursor: pointer; }
.clear { border: 0; background: none; color: var(--nv-accent); font-size: 14px;
         cursor: pointer; padding: 0 var(--s-3); font-family: inherit; }

.count { font-size: 14px; color: var(--nv-text-faint); margin: 0 0 var(--s-5); }

.month { margin-bottom: var(--s-6); }
.month h2 { display: flex; align-items: baseline; gap: 10px;
            font-size: 13px; letter-spacing: .06em; text-transform: uppercase;
            color: var(--nv-text-muted); font-weight: 600;
            border-bottom: 1px solid var(--nv-line);
            padding-bottom: var(--s-2); margin: 0 0 var(--s-3); }
.month h2 span { font-size: 12px; font-weight: 400; color: var(--nv-text-faint);
                 letter-spacing: 0; text-transform: none; }

.rows { list-style: none; margin: 0; padding: 0;
        display: flex; flex-direction: column; gap: 6px; }
.row { display: flex; align-items: center; gap: var(--s-4);
       padding: 12px 16px; background: var(--nv-surface);
       border: 1px solid var(--nv-line); border-radius: var(--r-sm);
       cursor: pointer;
       transition: border-color var(--dur-fast) var(--ease-out),
                   box-shadow var(--dur-fast) var(--ease-out); }
.row:hover { border-color: var(--nv-line-strong); box-shadow: var(--shadow-sm); }

.date { width: 58px; flex-shrink: 0; font-size: 13px; color: var(--nv-text-faint);
        font-variant-numeric: tabular-nums; }
.meta { flex: 1; min-width: 0; }
.t { display: block; font-size: 15px; font-weight: 600; color: var(--nv-text);
     line-height: 1.35; margin-bottom: 2px;
     overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sub { font-size: 13px; color: var(--nv-text-muted); }

.issue { font-size: 12px; padding: 4px 10px; border-radius: var(--r-full);
         background: var(--info-bg); color: var(--info); white-space: nowrap; }
.issue.standalone { background: var(--nv-bg); color: var(--nv-text-faint); }
.prem { font-size: 12px; padding: 4px 10px; border-radius: var(--r-full);
        background: var(--warn-bg); color: var(--warn); white-space: nowrap; }

@media (max-width: 700px) {
  .date, .prem { display: none; }
  .bar { flex-direction: column; }
  select, .search { width: 100%; }
}
</style>
