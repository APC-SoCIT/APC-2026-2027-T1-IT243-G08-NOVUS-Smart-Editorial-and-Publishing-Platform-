<script setup>
/* An open headline from the backlog: give it to a writer, or drop it.
   Both ask first (double take). */
import { ref, computed, onMounted } from 'vue'
import api from '../services/api'
import UiCombobox from './ui/UiCombobox.vue'
import { confirm } from '../composables/useConfirm'

const props = defineProps({ article: { type: Object, required: true } })
const emit = defineEmits(['done'])

const writers = ref([])
const writer = ref('')
const deadline = ref(props.article.deadline || '')
const dropping = ref(false)
const reason = ref('')
const busy = ref(false)
const error = ref('')

onMounted(async () => {
  const { data } = await api.get('/auth/writers/')
  writers.value = data
})

const writerOptions = computed(() =>
  writers.value.map((w) => ({ value: w.id, label: `${w.first_name} ${w.last_name}` })))
const writerName = computed(() =>
  writerOptions.value.find((o) => o.value === writer.value)?.label || 'the writer')

async function give() {
  error.value = ''
  if (!writer.value) { error.value = 'Choose the writer who will take it.'; return }
  if (!(await confirm({
    title: 'Give this headline to a writer?',
    message: `“${props.article.title}” will be assigned to ${writerName.value}.`,
    points: [
      'They are notified and it appears on their dashboard.',
      deadline.value ? `Deadline ${deadline.value}.` : 'No deadline set — it will not appear in overdue tracking.',
    ],
    confirmLabel: 'Assign',
  }))) return
  busy.value = true
  try {
    await api.post(`/editorial/articles/${props.article.id}/assign-writer/`,
                   { writer: writer.value, deadline: deadline.value || null })
    emit('done')
  } catch (e) {
    const d = e.response?.data
    error.value = d?.writer?.[0] || d?.deadline?.[0] || d?.detail || 'Could not assign it.'
  } finally { busy.value = false }
}

async function drop() {
  error.value = ''
  if (reason.value.trim().length < 5) { error.value = 'Say why it is being dropped.'; return }
  if (!(await confirm({
    title: 'Drop this headline?',
    message: `“${props.article.title}” leaves the backlog.`,
    points: ['The reason is recorded.', 'This cannot be undone from here.'],
    confirmLabel: 'Drop headline', tone: 'danger',
  }))) return
  busy.value = true
  try {
    await api.post(`/editorial/articles/${props.article.id}/withdraw/`, { reason: reason.value })
    emit('done')
  } catch (e) {
    error.value = e.response?.data?.reason?.[0] || e.response?.data?.detail || 'Could not drop it.'
  } finally { busy.value = false }
}
</script>

<template>
  <div class="form">
    <p class="now">
      <b>{{ article.title }}</b>
      <template v-if="article.category"><br />{{ article.category }}</template>
    </p>
    <p v-if="article.brief" class="brief">{{ article.brief }}</p>

    <template v-if="!dropping">
      <label>WRITER
        <UiCombobox v-model="writer" :options="writerOptions"
                    placeholder="Type a writer's name…" />
      </label>
      <label>DEADLINE
        <input v-model="deadline" type="date" />
      </label>
      <p v-if="error" class="err" role="alert">{{ error }}</p>
      <button class="primary" :disabled="busy" @click="give">
        {{ busy ? 'Assigning…' : 'Assign to writer' }}
      </button>
      <button class="link" type="button" @click="dropping = true; error = ''">
        Drop this headline instead
      </button>
    </template>

    <template v-else>
      <label>WHY IS IT BEING DROPPED?
        <textarea v-model="reason" rows="3"
                  placeholder="The story went stale, it is covered elsewhere…"></textarea>
      </label>
      <p v-if="error" class="err" role="alert">{{ error }}</p>
      <button class="danger" :disabled="busy" @click="drop">
        {{ busy ? 'Dropping…' : 'Drop headline' }}
      </button>
      <button class="link" type="button" @click="dropping = false; error = ''">
        Keep it in the backlog
      </button>
    </template>
  </div>
</template>

<style scoped>
.form { border: 1px solid var(--nv-line); border-radius: 8px; padding: 16px;
        background: var(--nv-bg); margin: 12px 0 6px; }
.now { font-size: 13px; line-height: 1.6; color: var(--nv-text-muted); margin: 0 0 10px; }
.now b { color: var(--nv-text); font-size: 14px; }
.brief { font-size: 13px; line-height: 1.6; color: var(--nv-text); margin: 0 0 16px;
         padding-left: 10px; border-left: 2px solid var(--nv-line-strong); }
label { display: block; font-size: 11px; color: var(--nv-text-muted); letter-spacing: .5px; margin-bottom: 12px; }
input, textarea { width: 100%; padding: 9px; border: 1px solid var(--nv-line-strong);
                  border-radius: 6px; font-size: 13px; margin-top: 5px; font-family: inherit; }
textarea { resize: vertical; }
.primary, .danger { width: 100%; padding: 11px; border: 0; color: #fff;
                    border-radius: 6px; font-weight: 600; cursor: pointer; }
.primary { background: var(--nv-navy-2); }
.danger { background: var(--bad); }
.primary:disabled, .danger:disabled { opacity: .55; }
.link { display: block; margin: 12px auto 0; background: none; border: 0; cursor: pointer;
        font-size: 13px; color: var(--nv-text-muted); text-decoration: underline; }
.err { color: var(--bad); font-size: 13px; }
</style>
