<script setup>
import { ref, onMounted } from 'vue'
import api from '../services/api'

const props = defineProps({
  articleId: { type: [Number, String], required: true },
  currentIssue: { type: [Number, null], default: null },
})
const emit = defineEmits(['assigned'])

const issues = ref([])
const selected = ref(props.currentIssue ?? '')
const busy = ref(false)
const error = ref('')
const ok = ref('')

onMounted(async () => {
  const { data } = await api.get('/publication/issues/')
  // Only issues that still accept articles (UC-1.11 E1).
  issues.value = (data.results ?? data)
    .filter(i => !['PUBLISHED', 'ARCHIVED'].includes(i.status))
})

async function save() {
  error.value = ''; ok.value = ''
  busy.value = true
  try {
    await api.post(`/editorial/articles/${props.articleId}/assign-issue/`,
                   { issue: selected.value || null })
    ok.value = selected.value ? 'Assigned to issue.' : 'Removed from issue.'
    emit('assigned')
  } catch (e) {
    error.value = e.response?.data?.detail || 'Could not assign.'
  } finally { busy.value = false }
}
</script>

<template>
  <div class="box">
    <h5>Issue assignment</h5>
    <p class="hint">
      An article assigned to an issue publishes with that issue. Leave it
      unassigned to publish it on its own.
    </p>
    <div class="row">
      <select v-model="selected">
        <option value="">Not assigned (standalone)</option>
        <option v-for="i in issues" :key="i.id" :value="i.id">
          Issue #{{ i.number }} — {{ i.title }}
        </option>
      </select>
      <button :disabled="busy" @click="save">
        {{ busy ? 'Saving…' : 'Save' }}
      </button>
    </div>
    <p v-if="error" class="err">{{ error }}</p>
    <p v-if="ok" class="ok">{{ ok }}</p>
  </div>
</template>

<style scoped>
.box { border: 1px solid #e6e6e6; border-radius: 8px; padding: 14px 16px;
       background: #fafafa; margin-top: 22px; }
h5 { margin: 0 0 6px; font-size: 12px; letter-spacing: .5px;
     text-transform: uppercase; color: #555; }
.hint { margin: 0 0 12px; font-size: 12px; color: #888; line-height: 1.5; }
.row { display: flex; gap: 8px; }
select { flex: 1; padding: 9px; border: 1px solid #ccc; border-radius: 6px; font-size: 13px; }
button { border: 1px solid #ccc; background: #fff; border-radius: 6px;
         padding: 9px 18px; font-size: 13px; cursor: pointer; }
button:disabled { opacity: .55; }
.err { color: #c00; font-size: 13px; margin: 10px 0 0; }
.ok { color: #0a7; font-size: 13px; margin: 10px 0 0; }
</style>
