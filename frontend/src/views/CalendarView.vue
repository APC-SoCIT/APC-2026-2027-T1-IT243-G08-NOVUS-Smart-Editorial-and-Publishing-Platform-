<script setup>
import { useAuthStore } from '../stores/auth'
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import api from '../services/api'
import StaffLayout from '../components/StaffLayout.vue'
import UiSkeleton from '../components/ui/UiSkeleton.vue'

const router = useRouter()
const auth = useAuthStore()

const today = new Date()
const year = ref(today.getFullYear())
const month = ref(today.getMonth() + 1)   // API expects 1-12
const data = ref({ events: [], open_deadlines: 0, overdue: 0 })
const loading = ref(true)
const showSettled = ref(false)

const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June',
                'July', 'August', 'September', 'October', 'November', 'December']

async function load() {
  loading.value = true
  try {
    const { data: d } = await api.get('/editorial/articles/calendar/', {
      params: { year: year.value, month: month.value },
    })
    data.value = d
  } finally { loading.value = false }
}
onMounted(load)

function step(n) {
  let m = month.value + n
  if (m < 1) { m = 12; year.value-- }
  if (m > 12) { m = 1; year.value++ }
  month.value = m
  load()
}

function goToday() {
  year.value = today.getFullYear()
  month.value = today.getMonth() + 1
  load()
}

/* A six-week grid starting on Monday, which is how editorial weeks are
   counted. Leading and trailing days belong to neighbouring months and are
   shown greyed rather than blank, so the weeks read continuously. */
const grid = computed(() => {
  const first = new Date(year.value, month.value - 1, 1)
  const offset = (first.getDay() + 6) % 7        // Monday = 0
  const start = new Date(year.value, month.value - 1, 1 - offset)

  // Settled work is history. A month of strikethrough buries the two
  // things that still need doing, so it is off by default.
  const visible = showSettled.value
    ? data.value.events
    : data.value.events.filter(e =>
        e.kind === 'deadline' ? e.is_open : !e.shipped)

  const byDate = {}
  for (const e of visible) {
    (byDate[e.date] ||= []).push(e)
  }

  const todayKey = new Date().toISOString().slice(0, 10)

  return Array.from({ length: 42 }, (_, i) => {
    const d = new Date(start)
    d.setDate(start.getDate() + i)
    const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
    return {
      key,
      day: d.getDate(),
      outside: d.getMonth() + 1 !== month.value,
      isToday: key === todayKey,
      events: byDate[key] || [],
    }
  })
})

const hasEvents = computed(() => data.value.events.length > 0)

function openEvent(e) {
  // Each role opens the event in its own workspace. Where a role has no part
  // in the event, the entry stays on the calendar as information only.
  function destination(ev) {
    const role = auth.user?.role ?? auth.role
    if (ev.kind === 'deadline') {
      return { WRITER: `/writer/compose/${ev.id}`,
               EDITOR: `/editor/review/${ev.id}`,
               ADMIN: `/editor/review/${ev.id}` }[role] || null
    }
    return { PUBLISHER: `/publisher/issue/${ev.id}`,
             ADMIN: `/publisher/issue/${ev.id}`,
             EDITOR: '/issues-overview',
             GRAPHIC_DESIGNER: '/issues-overview' }[role] || null
  }
  const to = destination(e)
  if (to) router.push(to)
}
</script>

<template>
  <StaffLayout title="Calendar"
               subtitle="Deadlines and issue release dates">

    <div class="bar">
      <div class="nav">
        <button aria-label="Previous month" @click="step(-1)">‹</button>
        <h2>{{ MONTHS[month - 1] }} {{ year }}</h2>
        <button aria-label="Next month" @click="step(1)">›</button>
      </div>
      <button class="today" @click="goToday">Today</button>
      <label class="settled">
        <input type="checkbox" v-model="showSettled" />
        Show settled
      </label>

      <div class="tally" role="status">
        <span><b>{{ data.open_deadlines }}</b> open</span>
        <span v-if="data.overdue" class="late">
          <b>{{ data.overdue }}</b> overdue
        </span>
      </div>
    </div>

    <UiSkeleton v-if="loading" :rows="4" label="Loading the calendar" />

    <template v-else>
      <div class="grid" role="grid" :aria-label="`${MONTHS[month - 1]} ${year}`">
        <div v-for="d in ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']" :key="d"
             class="dow">{{ d }}</div>

        <div v-for="cell in grid" :key="cell.key" class="cell"
             :class="{ outside: cell.outside, today: cell.isToday }" role="gridcell">
          <span class="dnum">{{ cell.day }}</span>

          <button v-for="e in cell.events" :key="`${e.kind}-${e.id}`"
                  class="event"
                  :class="[e.kind, {
                    overdue: e.is_overdue,
                    done: e.kind === 'deadline' ? !e.is_open : e.shipped,
                    atrisk: e.kind === 'release' && !e.is_ready && !e.shipped,
                  }]"
                  :title="e.kind === 'release'
                    ? `${e.title} — ${e.approved_articles} of ${e.total_articles} approved`
                    : `${e.title} — ${e.writer}`"
                  @click="openEvent(e)">
            {{ e.title }}
          </button>
        </div>
      </div>

      <p v-if="!hasEvents" class="none">
        Nothing scheduled this month. Deadlines appear here when an editor
        assigns an article with one; release dates appear when the publisher
        sets a target on an issue.
      </p>

      <div class="key">
        <span><i class="k deadline"></i> Deadline</span>
        <span><i class="k overdue"></i> Overdue</span>
        <span><i class="k release"></i> Issue release</span>
        <span><i class="k atrisk"></i> Release at risk</span>
        <span><i class="k done"></i> Settled</span>
      </div>

      <p class="caveat">
        Only commissioned articles carry a deadline, so a writer's own draft
        will not appear. An issue's target date is an intention rather than a
        commitment — nothing publishes an issue automatically, and a target
        shown in amber cannot currently be met.
      </p>
    </template>
  </StaffLayout>
</template>

<style scoped>
.bar { display: flex; align-items: center; gap: var(--s-4);
       margin-bottom: var(--s-4); flex-wrap: wrap; }
.nav { display: flex; align-items: center; gap: var(--s-3); }
.nav button { width: 34px; height: 34px; border: 1px solid var(--nv-line-strong);
              background: var(--nv-surface); color: var(--nv-text);
              border-radius: var(--r-sm); font-size: 18px; cursor: pointer; }
.nav button:hover { border-color: var(--nv-accent); color: var(--nv-accent); }
.nav h2 { margin: 0; font-size: 19px; min-width: 190px; text-align: center;
          color: var(--nv-text); }
.today { border: 1px solid var(--nv-line-strong); background: var(--nv-surface);
         color: var(--nv-text); border-radius: var(--r-sm);
         padding: 8px 14px; font-size: 14px; cursor: pointer; font-family: inherit; }
.settled { display: flex; align-items: center; gap: 7px; font-size: 14px;
           color: var(--nv-text-muted); cursor: pointer; }
.settled input { cursor: pointer; }
.tally { margin-left: auto; display: flex; gap: var(--s-4); font-size: 14px;
         color: var(--nv-text-muted); }
.tally b { color: var(--nv-text); }
.tally .late b { color: var(--bad); }

.grid { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr));
        gap: 1px; background: var(--nv-line);
        border: 1px solid var(--nv-line); border-radius: var(--r-md);
        overflow: hidden; }
.dow { background: var(--nv-bg); padding: 10px; text-align: center;
       font-size: 12px; letter-spacing: .05em; text-transform: uppercase;
       color: var(--nv-text-faint); font-weight: 600; }

.cell { background: var(--nv-surface); min-height: 112px; padding: 5px;
        display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.cell.outside { background: var(--nv-bg); }
.cell.outside .dnum { color: var(--nv-text-faint); opacity: .5; }
.cell.today { box-shadow: inset 0 0 0 2px var(--nv-accent); }
.dnum { font-size: 11px; color: var(--nv-text-faint); font-weight: 500;
        font-variant-numeric: tabular-nums; padding: 1px 3px; }
.cell.today { box-shadow: inset 0 0 0 2px var(--nv-accent); }
.cell.today .dnum { color: #fff; background: var(--nv-accent);
                    font-weight: 700; border-radius: var(--r-full);
                    width: 20px; height: 20px; display: flex;
                    align-items: center; justify-content: center;
                    padding: 0; }

.event { display: block; width: 100%; text-align: left; border: 0;
         border-left: 3px solid; border-radius: 3px; padding: 4px 6px;
         font-size: 11px; line-height: 1.35; cursor: pointer;
         font-family: inherit; overflow: hidden; text-overflow: ellipsis;
         white-space: nowrap; min-width: 0;
         transition: filter var(--dur-fast) var(--ease-out); }
.event:hover { filter: brightness(.96); }
.event.deadline { background: var(--info-bg); border-color: var(--info);
                  color: var(--info); }
.event.release { background: var(--nv-accent-soft); border-color: var(--nv-navy-2);
                 color: var(--nv-navy-2); font-weight: 600; }
.event.overdue { background: var(--bad-bg); border-color: var(--bad);
                 color: var(--bad); font-weight: 600; }
.event.atrisk { background: var(--warn-bg); border-color: var(--warn);
                color: var(--warn); }
.event.done { background: transparent; border-color: var(--nv-line-strong);
              color: var(--nv-text-faint); font-weight: 400; opacity: .7; }
.event.done:hover { opacity: 1; }

.none { margin: var(--s-5) 0 0; font-size: 14px; line-height: 1.6;
        color: var(--nv-text-faint); }

.key { display: flex; gap: var(--s-5); flex-wrap: wrap;
       margin-top: var(--s-4); font-size: 13px; color: var(--nv-text-muted); }
.key span { display: flex; align-items: center; gap: 7px; }
.k { width: 12px; height: 12px; border-radius: 2px; border-left: 3px solid; }
.k.deadline { background: var(--info-bg); border-color: var(--info); }
.k.overdue { background: var(--bad-bg); border-color: var(--bad); }
.k.release { background: var(--nv-accent-soft); border-color: var(--nv-navy-2); }
.k.atrisk { background: var(--warn-bg); border-color: var(--warn); }
.k.done { background: var(--nv-bg); border-color: var(--nv-line-strong); }

.caveat { margin-top: var(--s-4); font-size: 13px; line-height: 1.6;
          color: var(--nv-text-faint); max-width: 70ch; }

@media (max-width: 760px) {
  .cell { min-height: 76px; }
  .event { font-size: 10px; }
  .tally { width: 100%; margin-left: 0; }
}
</style>
