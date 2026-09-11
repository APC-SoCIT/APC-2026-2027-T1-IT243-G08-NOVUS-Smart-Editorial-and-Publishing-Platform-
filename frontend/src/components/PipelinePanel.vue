<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../services/api'

const router = useRouter()
const data = ref(null)
const loading = ref(true)

onMounted(async () => {
  try {
    const r = await api.get('/editorial/articles/pipeline/')
    data.value = r.data
  } finally { loading.value = false }
})

const label = (s) => s.replace(/_/g, ' ').toLowerCase()
</script>

<template>
  <div v-if="!loading && data" class="panel">
    <h3>Pipeline overview</h3>

    <div class="stats">
      <div class="stat"><b>{{ data.open }}</b><span>IN PROGRESS</span></div>
      <div class="stat" :class="{ warn: data.due_soon }">
        <b>{{ data.due_soon }}</b><span>DUE SOON</span>
      </div>
      <div class="stat" :class="{ bad: data.overdue }">
        <b>{{ data.overdue }}</b><span>OVERDUE</span>
      </div>
      <div class="stat"><b>{{ data.unassigned_to_issue }}</b><span>UNASSIGNED</span></div>
    </div>

    <div v-if="data.overdue_articles.length" class="overdue">
      <h4>Overdue</h4>
      <div v-for="a in data.overdue_articles" :key="a.id" class="orow"
           @click="router.push(`/editor/review/${a.id}`)">
        <div>
          <span class="t">{{ a.title }}</span>
          <em>{{ a.writer_name }} · {{ label(a.status) }}</em>
        </div>
        <span class="days">{{ Math.abs(a.days_to_deadline) }}d late</span>
      </div>
    </div>

    <div v-if="data.workload.length" class="workload">
      <h4>Writer workload</h4>
      <div v-for="w in data.workload" :key="w.writer" class="wrow">
        <span class="name">{{ w.writer }}</span>
        <div class="bars">
          <i v-for="n in w.open" :key="n"
             :class="{ late: n <= w.overdue }"></i>
        </div>
        <span class="count">
          {{ w.open }} open<template v-if="w.overdue">, {{ w.overdue }} late</template>
        </span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.panel { border: 1px solid #eee; border-radius: 10px; padding: 18px; margin-top: 24px; }
h3 { margin: 0 0 14px; font-size: 15px; }
h4 { margin: 20px 0 9px; font-size: 12px; letter-spacing: .5px;
     text-transform: uppercase; color: #777; }
.stats { display: flex; gap: 10px; }
.stat { flex: 1; border: 1px solid #eee; border-radius: 8px; padding: 14px; text-align: center; }
.stat b { display: block; font-size: 26px; }
.stat span { font-size: 10px; color: #999; letter-spacing: .5px; }
.stat.warn { border-color: #f0d9b5; background: #fffdf8; }
.stat.warn b { color: #96631a; }
.stat.bad { border-color: #f0c9c9; background: #fffafa; }
.stat.bad b { color: #a33; }
.orow { display: flex; justify-content: space-between; align-items: center;
        padding: 10px 0; border-bottom: 1px solid #f2f2f2; cursor: pointer; }
.orow:hover { background: #fafafa; }
.t { display: block; font-size: 14px; font-weight: 600; }
em { font-size: 12px; color: #888; font-style: normal; text-transform: capitalize; }
.days { font-size: 11px; padding: 4px 10px; border-radius: 12px;
        background: #fbe6e6; color: #a33; white-space: nowrap; }
.wrow { display: flex; align-items: center; gap: 12px; padding: 7px 0; }
.name { width: 130px; font-size: 13px; }
.bars { display: flex; gap: 3px; flex: 1; }
.bars i { width: 9px; height: 18px; border-radius: 2px; background: #cddcee; }
.bars i.late { background: #d99; }
.count { font-size: 11px; color: #999; white-space: nowrap; }
</style>
