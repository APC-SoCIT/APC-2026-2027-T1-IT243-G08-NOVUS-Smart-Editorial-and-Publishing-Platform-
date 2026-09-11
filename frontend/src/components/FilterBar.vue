<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  statuses: { type: Array, default: () => [] },
  showOverdue: { type: Boolean, default: true },
})
const emit = defineEmits(['change'])

const q = ref('')
const status = ref('')
const category = ref('')
const overdue = ref(false)
const sort = ref('-updated_at')

const CATEGORIES = ['Business', 'Tech', 'Life', 'Innovation', 'Leadership']

const openPanel = ref(false)
let debounce = null
function push() {
  emit('change', {
    q: q.value || undefined,
    status: status.value || undefined,
    category: category.value || undefined,
    overdue: overdue.value ? 'true' : undefined,
    sort: sort.value,
  })
}

// Typing shouldn't fire a request per keystroke.
watch(q, () => {
  clearTimeout(debounce)
  debounce = setTimeout(push, 300)
})
watch([status, category, overdue, sort], push)

function clear() {
  q.value = ''; status.value = ''; category.value = ''
  overdue.value = false; sort.value = '-updated_at'
}

const dirty = () => q.value || status.value || category.value || overdue.value
const label = (s) => s.replace(/_/g, ' ').toLowerCase()
</script>

<template>
  <div class="bar">
    <input v-model="q" class="search" type="search"
           aria-label="Search articles"
           placeholder="Search titles, excerpts, or writers…" />

    <button class="toggle" :class="{ on: openPanel || dirty() }"
            :aria-expanded="openPanel" aria-controls="filter-panel"
            @click="openPanel = !openPanel">
      Filters
      <span v-if="dirty()" class="dot" aria-hidden="true"></span>
    </button>

    <div v-show="openPanel" id="filter-panel" class="panel">

    <select v-if="statuses.length" v-model="status">
      <option value="">All statuses</option>
      <option v-for="s in statuses" :key="s" :value="s">{{ label(s) }}</option>
    </select>

    <select v-model="category">
      <option value="">All categories</option>
      <option v-for="c in CATEGORIES" :key="c" :value="c">{{ c }}</option>
    </select>

    <select v-model="sort">
      <option value="-updated_at">Recently updated</option>
      <option value="deadline">Deadline soonest</option>
      <option value="-created_at">Newest first</option>
      <option value="title">Title A–Z</option>
    </select>

    <label v-if="showOverdue" class="chk">
      <input type="checkbox" v-model="overdue" />
      Overdue only
    </label>

      <button v-if="dirty()" class="clear" @click="clear">Clear all</button>
    </div>
  </div>
</template>

<style scoped>
/* Search stays visible; the rest is one click away. Four controls above
   three results announces itself more than it helps. */
.bar { position: relative; display: flex; gap: var(--s-2); align-items: center;
       margin-bottom: var(--s-4); }
.toggle { display: inline-flex; align-items: center; gap: var(--s-2);
          background: var(--nv-surface); border: 1px solid var(--nv-line-strong);
          border-radius: var(--r-sm); padding: 9px var(--s-4);
          font-size: var(--t-sm); color: var(--nv-text-muted); cursor: pointer;
          white-space: nowrap;
          transition: border-color var(--dur-fast) var(--ease-out); }
.toggle:hover { border-color: var(--nv-text-faint); color: var(--nv-text); }
.toggle.on { border-color: var(--nv-navy-2); color: var(--nv-navy-2); font-weight: 600; }
.dot { width: 6px; height: 6px; border-radius: 50%; background: var(--nv-accent); }
.panel { position: absolute; right: 0; top: calc(100% + 6px); z-index: 20;
         display: flex; flex-direction: column; gap: var(--s-3);
         background: var(--nv-surface); border: 1px solid var(--nv-line);
         border-radius: var(--r-md); padding: var(--s-4);
         box-shadow: var(--shadow-md); min-width: 240px; }
.search { flex: 1; min-width: 200px; padding: 9px var(--s-4);
          border: 1px solid var(--nv-line-strong); border-radius: var(--r-sm);
          font-size: var(--t-sm); font-family: inherit;
          background: var(--nv-surface); }
.search:focus { outline: none; border-color: #4a7fb5;
                box-shadow: 0 0 0 3px rgba(74,127,181,.12); }
select { padding: 9px 10px; border: 1px solid #d7dbe0; border-radius: 7px;
         font-size: 13px; font-family: inherit; background: #fff;
         text-transform: capitalize; cursor: pointer; }
.chk { display: flex; align-items: center; gap: 6px; font-size: 13px;
       color: #556; cursor: pointer; white-space: nowrap; }
.chk input { cursor: pointer; }
.clear { border: 0; background: none; color: #4a7fb5; font-size: 13px;
         cursor: pointer; padding: 8px; }
</style>
