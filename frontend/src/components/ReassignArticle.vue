<script setup>
/* UC-1.1 A3: hand an unsubmitted assignment to another writer. The draft
   goes with it; both writers are notified by the server. */
import { ref, computed, onMounted } from 'vue'
import api from '../services/api'
import ConfirmDialog from './ConfirmDialog.vue'

const props = defineProps({ article: { type: Object, required: true } })
const emit = defineEmits(['reassigned'])

const writers = ref([])
const writer = ref('')
const deadline = ref(props.article.deadline || '')
const busy = ref(false)
const error = ref('')
const confirming = ref(false)

onMounted(async () => {
  const { data } = await api.get('/auth/writers/')
  writers.value = data.filter((w) => w.id !== props.article.writer)
})

const newName = computed(() => {
  const w = writers.value.find((x) => x.id === writer.value)
  return w ? `${w.first_name} ${w.last_name}` : 'the new writer'
})

function review() {
  error.value = ''
  if (!writer.value) { error.value = 'Choose the writer who will take it over.'; return }
  confirming.value = true
}

async function submit() {
  confirming.value = false
  busy.value = true
  try {
    await api.post(`/editorial/articles/${props.article.id}/reassign/`, {
      writer: writer.value,
      deadline: deadline.value || null,
    })
    emit('reassigned')
  } catch (e) {
    const d = e.response?.data
    error.value = d?.writer?.[0] || d?.deadline?.[0] || d?.[0] || d?.detail
      || 'Could not reassign the article.'
  } finally { busy.value = false }
}
</script>

<template>
  <div class="form">
    <p class="now">
      <b>{{ article.title }}</b><br />
      Now with {{ article.writer_name }}
      <template v-if="article.status === 'DRAFTING'"> · draft started</template>
    </p>
    <label>NEW WRITER
      <select v-model="writer">
        <option value="">Select a writer…</option>
        <option v-for="w in writers" :key="w.id" :value="w.id">
          {{ w.first_name }} {{ w.last_name }}
        </option>
      </select>
    </label>
    <label>DEADLINE
      <input v-model="deadline" type="date" />
    </label>
    <p v-if="error" class="err" role="alert">{{ error }}</p>
    <button class="primary" :disabled="busy" @click="review">
      {{ busy ? 'Reassigning…' : 'Reassign' }}
    </button>
  </div>

  <ConfirmDialog
    :open="confirming"
    title="Reassign this article?"
    :message="`“${article.title}” will move from ${article.writer_name} to ${newName}.`"
    confirm-label="Reassign"
    :points="[
      article.status === 'DRAFTING'
        ? 'The draft so far goes with it.'
        : 'The writer has not started it yet.',
      'Both writers are notified.',
    ]"
    @confirm="submit"
    @cancel="confirming = false" />
</template>

<style scoped>
.form { border: 1px solid var(--nv-line); border-radius: 8px; padding: 16px;
        background: var(--nv-bg); margin: 12px 0 6px; }
.now { font-size: 13px; line-height: 1.6; color: var(--nv-text-muted); margin: 0 0 16px; }
.now b { color: var(--nv-text); font-size: 14px; }
label { display: block; font-size: 11px; color: var(--nv-text-muted); letter-spacing: .5px; margin-bottom: 12px; }
input, select { width: 100%; padding: 9px; border: 1px solid var(--nv-line-strong);
                border-radius: 6px; font-size: 13px; margin-top: 5px; font-family: inherit; }
.primary { width: 100%; padding: 11px; border: 0; background: var(--nv-navy-2); color: #fff;
           border-radius: 6px; font-weight: 600; cursor: pointer; }
.primary:disabled { opacity: .55; }
.err { color: var(--bad); font-size: 13px; }
</style>
