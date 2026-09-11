<script setup>
import { ref, onMounted, computed } from 'vue'
import api from '../services/api'
import StaffLayout from '../components/StaffLayout.vue'
import ChartCard from '../components/charts/ChartCard.vue'

const tab = ref('evaluation')
const days = ref(90)
const data = ref({})
const loading = ref(true)
const error = ref('')

const TABS = [
  { key: 'evaluation', label: 'AI evaluation' },
  { key: 'pipeline', label: 'Editorial pipeline' },
  { key: 'production', label: 'Production' },
  { key: 'revenue', label: 'Subscriptions' },
]

async function load() {
  loading.value = true
  error.value = ''
  try {
    const { data: d } = await api.get(`/reports/${tab.value}/`, {
      params: { days: days.value },
    })
    data.value = d
  } catch (e) {
    error.value = e.response?.data?.detail || 'Could not load this report.'
  } finally { loading.value = false }
}
onMounted(load)

function pick(k) { tab.value = k; load() }

const T = () => data.value.threshold ?? 70

const scoreChart = computed(() => {
  const d = data.value.distribution || []
  return {
    series: [{ name: 'Evaluations', data: d.map(b => b.count) }],
    options: {
      chart: { type: 'bar' },
      plotOptions: { bar: { columnWidth: '62%', borderRadius: 3, distributed: true } },
      legend: { show: false },
      // Bands below the passing mark are red, so the gate reads at a glance.
      colors: d.map(b => parseInt(b.band) < T() ? '#c95757' : '#4a7fb5'),
      xaxis: { categories: d.map(b => b.band) },
    },
  }
})

const gateChart = computed(() => ({
  series: [data.value.passed || 0, data.value.failed || 0],
  options: {
    chart: { type: 'donut' },
    labels: ['Passed to editor', 'Returned to writer'],
    colors: ['#1c6b45', '#c95757'],
    plotOptions: { pie: { donut: { size: '68%' } } },
    stroke: { width: 0 },
  },
}))

const statusChart = computed(() => {
  const e = Object.entries(data.value.by_status || {}).filter(([, n]) => n > 0)
  return {
    series: [{ name: 'Articles', data: e.map(([, n]) => n) }],
    options: {
      chart: { type: 'bar' },
      plotOptions: { bar: { horizontal: true, borderRadius: 3, barHeight: '58%' } },
      xaxis: { categories: e.map(([k]) => k.replace(/_/g, ' ').toLowerCase()) },
      colors: ['#4a7fb5'],
    },
  }
})

const writerChart = computed(() => {
  const w = (data.value.writers || []).slice(0, 8)
  return {
    series: [
      { name: 'Published', data: w.map(x => x.published) },
      { name: 'In progress', data: w.map(x => x.open) },
      { name: 'Overdue', data: w.map(x => x.overdue) },
    ],
    options: {
      chart: { type: 'bar', stacked: true },
      plotOptions: { bar: { columnWidth: '52%', borderRadius: 3 } },
      colors: ['#1c6b45', '#4a7fb5', '#c95757'],
      xaxis: { categories: w.map(x => `${x.first_name} ${x.last_name.charAt(0)}.`) },
    },
  }
})

const maxBand = computed(() =>
  Math.max(1, ...(data.value.distribution || []).map(b => b.count)))

function exportCsv() {
  const d = data.value
  const rows = [['Report', tab.value], ['Window (days)', d.window_days], []]
  Object.entries(d).forEach(([k, v]) => {
    if (typeof v !== 'object' || v === null) rows.push([k, v])
  })
  const csv = rows.map(r => r.join(',')).join('\n')
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }))
  const a = document.createElement('a')
  a.href = url
  a.download = `novus-${tab.value}-report.csv`
  a.click()
  URL.revokeObjectURL(url)
}

const pct = (n, total) => total ? Math.round((n / total) * 100) : 0
const label = (s) => (s || '').replace(/_/g, ' ').toLowerCase()
</script>

<template>
  <StaffLayout title="Reports" subtitle="Pipeline, evaluation, and subscription figures">
    <div class="controls">
      <div class="tabs">
        <button v-for="t in TABS" :key="t.key"
                :class="{ on: tab === t.key }" @click="pick(t.key)">
          {{ t.label }}
        </button>
      </div>
      <select v-model="days" @change="load">
        <option :value="30">Last 30 days</option>
        <option :value="90">Last 90 days</option>
        <option :value="365">Last year</option>
      </select>
      <button class="csv" @click="exportCsv">Export CSV</button>
    </div>

    <p v-if="error" class="err" role="alert">{{ error }}</p>
    <p v-else-if="loading">Loading…</p>

    <!-- AI evaluation -->
    <template v-else-if="tab === 'evaluation'">
      <div v-if="data.seeded_present" class="warnbox">
        Some evaluations in this window were generated for demonstration and
        are not live AI output.
      </div>

      <div class="stats">
        <div class="stat"><b>{{ data.total_evaluations }}</b><span>EVALUATIONS</span></div>
        <div class="stat ok"><b>{{ data.pass_rate ?? '—' }}%</b><span>PASS RATE</span></div>
        <div class="stat"><b>{{ data.averages?.overall ?? '—' }}</b><span>AVG SCORE</span></div>
        <div class="stat warn"><b>{{ data.override_rate ?? '—' }}%</b><span>OVERRIDE RATE</span></div>
      </div>

      <ChartCard
        title="Score distribution"
        :caption="`Passing mark is ${data.threshold}. Red bands were returned to their writer.`"
        type="bar"
        :series="scoreChart.series"
        :options="scoreChart.options"
        :description="`Bar chart of evaluation scores in ten-point bands. ${data.passed} of ${data.total_evaluations} scored at or above ${data.threshold}.`" />

      <ChartCard
        title="Gate outcomes"
        caption="How submissions divided at the pre-screening threshold."
        type="donut"
        :height="280"
        :series="gateChart.series"
        :options="gateChart.options"
        :description="`${data.passed} evaluations passed to an editor and ${data.failed} were returned.`" />

      <div class="two">
        <div class="card">
          <h4>Component averages</h4>
          <div class="metric">
            <span>Grammar</span>
            <div class="track"><i :style="{ width: (data.averages?.grammar || 0) + '%' }"></i></div>
            <b>{{ data.averages?.grammar ?? '—' }}</b>
          </div>
          <div class="metric">
            <span>Readability</span>
            <div class="track"><i :style="{ width: (data.averages?.readability || 0) + '%' }"></i></div>
            <b>{{ data.averages?.readability ?? '—' }}</b>
          </div>
        </div>

        <div class="card">
          <h4>Most flagged</h4>
          <p v-if="!data.common_issues?.length" class="muted">Nothing flagged.</p>
          <ul v-else class="list">
            <li v-for="c in data.common_issues" :key="c.note_type">
              <span>{{ label(c.note_type) }}</span><b>{{ c.count }}</b>
            </li>
          </ul>
        </div>
      </div>
    </template>

    <!-- pipeline -->
    <template v-else-if="tab === 'pipeline'">
      <div class="stats">
        <div class="stat"><b>{{ data.total }}</b><span>ARTICLES</span></div>
        <div class="stat ok"><b>{{ data.published }}</b><span>PUBLISHED</span></div>
        <div class="stat bad"><b>{{ data.overdue_now }}</b><span>OVERDUE</span></div>
        <div class="stat"><b>{{ data.avg_turnaround_days ?? '—' }}</b><span>AVG DAYS</span></div>
      </div>

      <ChartCard
        title="Articles by status"
        caption="Where work currently sits in the pipeline."
        type="bar"
        :series="statusChart.series"
        :options="statusChart.options"
        :description="`Horizontal bar chart of ${data.total} articles grouped by workflow status.`" />

      <div class="card">
        <h4>Writer output</h4>
        <table>
          <thead><tr><th>Writer</th><th>Total</th><th>Published</th><th>Open</th><th>Overdue</th></tr></thead>
          <tbody>
            <tr v-for="w in data.writers" :key="w.id">
              <td>{{ w.first_name }} {{ w.last_name }}</td>
              <td class="c">{{ w.total }}</td>
              <td class="c">{{ w.published }}</td>
              <td class="c">{{ w.open }}</td>
              <td class="c" :class="{ red: w.overdue }">{{ w.overdue }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <!-- production -->
    <template v-else-if="tab === 'production'">
      <div class="stats">
        <div class="stat"><b>{{ data.layouts_submitted }}</b><span>LAYOUTS</span></div>
        <div class="stat ok"><b>{{ data.layouts_approved }}</b><span>APPROVED</span></div>
        <div class="stat warn"><b>{{ data.layouts_revised }}</b><span>REVISED</span></div>
        <div class="stat"><b>{{ data.superseded_versions }}</b><span>SUPERSEDED</span></div>
      </div>

      <div class="card">
        <h4>Issue readiness</h4>
        <table>
          <thead><tr><th>Issue</th><th>Status</th><th>Articles</th><th>Approved</th></tr></thead>
          <tbody>
            <tr v-for="i in data.issues" :key="i.id">
              <td>#{{ i.number }} — {{ i.title }}</td>
              <td>{{ label(i.status) }}</td>
              <td class="c">{{ i.articles }}</td>
              <td class="c">{{ i.approved }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <!-- revenue -->
    <template v-else>
      <div class="warnbox">{{ data.note }}</div>
      <div class="stats">
        <div class="stat ok"><b>{{ data.subscribers }}</b><span>SUBSCRIBERS</span></div>
        <div class="stat"><b>{{ data.free_readers }}</b><span>FREE READERS</span></div>
        <div class="stat"><b>{{ data.new_subscribers }}</b><span>NEW THIS PERIOD</span></div>
        <div class="stat"><b>{{ data.premium_articles }}</b><span>PREMIUM ARTICLES</span></div>
      </div>
      <div class="card">
        <h4>Digital editions</h4>
        <div class="metric">
          <span>Issues published</span>
          <div class="track"><i style="width:100%"></i></div>
          <b>{{ data.issues_published }}</b>
        </div>
        <div class="metric">
          <span>With a downloadable replica</span>
          <div class="track">
            <i :style="{ width: pct(data.issues_with_replica, data.issues_published) + '%' }"></i>
          </div>
          <b>{{ data.issues_with_replica }}</b>
        </div>
      </div>
    </template>
  </StaffLayout>
</template>

<style scoped>
.controls { display: flex; gap: 10px; align-items: center; margin-bottom: 20px;
            flex-wrap: wrap; }
.tabs { display: flex; gap: 4px; flex: 1; }
.tabs button { border: 1px solid #dde1e6; background: #fff; border-radius: 7px;
               padding: 8px 14px; font-size: 13px; cursor: pointer; }
.tabs button.on { background: #1a2744; color: #fff; border-color: #1a2744; }
select, .csv { padding: 8px 12px; border: 1px solid #d7dbe0; border-radius: 7px;
               font-size: 13px; background: #fff; cursor: pointer; font-family: inherit; }
.err { background: #fdeeee; border: 1px solid #f0cfcf; color: #a33;
       padding: 11px 14px; border-radius: 8px; font-size: 13px; }
.warnbox { background: #fdf6e8; border: 1px solid #f0d9b5; color: #8a6321;
           padding: 11px 14px; border-radius: 8px; font-size: 13px;
           line-height: 1.6; margin-bottom: 18px; }
.stats { display: flex; gap: 10px; margin-bottom: 18px; }
.stat { flex: 1; background: #fff; border: 1px solid #eaecef; border-radius: 9px;
        padding: 16px; text-align: center; }
.stat b { display: block; font-size: 26px; }
.stat span { font-size: 10px; color: #99a; letter-spacing: .5px; }
.stat.ok b { color: #1c6b45; }
.stat.warn b { color: #96631a; }
.stat.bad b { color: #a33; }
.card { background: #fff; border: 1px solid #eaecef; border-radius: 9px;
        padding: 18px; margin-bottom: 16px; }
.two { display: flex; gap: 16px; }
.two .card { flex: 1; }
h4 { margin: 0 0 4px; font-size: 14px; }
.cap { margin: 0 0 16px; font-size: 12px; color: #99a; }
.muted { color: #99a; font-size: 13px; margin: 0; }
.hist { display: flex; gap: 6px; align-items: flex-end; height: 160px; }
.bar { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 4px;
       height: 100%; }
.col { flex: 1; width: 100%; display: flex; align-items: flex-end; }
.fill { width: 100%; background: #4a7fb5; border-radius: 3px 3px 0 0; min-height: 2px; }
.fill.under { background: #d99; }
.n { font-size: 11px; color: #778; }
.lbl { font-size: 9px; color: #aab; }
.metric { display: flex; align-items: center; gap: 12px; margin-bottom: 9px; }
.metric span { width: 190px; font-size: 13px; color: #556; text-transform: capitalize; }
.track { flex: 1; height: 7px; background: #eef1f4; border-radius: 4px; overflow: hidden; }
.track i { display: block; height: 100%; background: #4a7fb5; }
.metric b { width: 40px; text-align: right; font-size: 13px; }
.list { list-style: none; margin: 0; padding: 0; }
.list li { display: flex; justify-content: space-between; padding: 7px 0;
           border-bottom: 1px solid #f2f4f6; font-size: 13px; text-transform: capitalize; }
table { width: 100%; border-collapse: collapse; }
th { text-align: left; font-size: 10px; letter-spacing: .7px; text-transform: uppercase;
     color: #99a; padding: 8px 6px; border-bottom: 1px solid #eaecef; }
td { padding: 9px 6px; border-bottom: 1px solid #f4f6f8; font-size: 13px; }
td.c { text-align: center; }
td.red { color: #a33; font-weight: 600; }
</style>
