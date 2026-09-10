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
           placeholder="Search titles, excerpts, or writers…" />

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

    <button v-if="dirty()" class="clear" @click="clear">Clear</button>
  </div>
</template>

<style scoped>
.bar { display: flex; gap: 8px; align-items: center; flex-wrap: wrap;
       padding: 12px; background: #fff; border: 1px solid #eaecef;
       border-radius: 10px; margin-bottom: 18px; }
.search { flex: 1; min-width: 200px; padding: 9px 12px; border: 1px solid #d7dbe0;
          border-radius: 7px; font-size: 13px; font-family: inherit; }
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
