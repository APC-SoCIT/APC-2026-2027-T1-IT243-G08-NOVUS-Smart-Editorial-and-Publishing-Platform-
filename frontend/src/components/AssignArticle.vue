<script setup>
import { ref, onMounted } from 'vue'
import api from '../services/api'

const emit = defineEmits(['assigned'])

const writers = ref([])
const open = ref(false)
const busy = ref(false)
const error = ref('')

const form = ref({ title: '', brief: '', category: '', writer: '', deadline: '' })

onMounted(async () => {
  const { data } = await api.get('/auth/writers/')
  writers.value = data
})

function reset() {
  form.value = { title: '', brief: '', category: '', writer: '', deadline: '' }
  error.value = ''
}

async function submit() {
  error.value = ''
  if (!form.value.title.trim() || !form.value.writer) {
    error.value = 'A topic and a writer are required.'
    return
  }
  busy.value = true
  try {
    await api.post('/editorial/articles/assign/', {
      title: form.value.title,
      brief: form.value.brief,
      category: form.value.category,
      writer: form.value.writer,
      deadline: form.value.deadline || null,
    })
    reset()
    open.value = false
    emit('assigned')
  } catch (e) {
    const d = e.response?.data
    error.value = d?.writer?.[0] || d?.detail || 'Could not create the assignment.'
  } finally { busy.value = false }
}
</script>

<template>
  <div class="head">
    <h3>Assignments</h3>
    <button class="new" @click="open = !open">
      {{ open ? 'Cancel' : '+ Assign Article' }}
    </button>
  </div>

  <div v-if="open" class="form">
    <label>TOPIC / HEADLINE
      <input v-model="form.title" placeholder="What should the writer cover?" />
    </label>
    <label>ANGLE / BRIEF
      <textarea v-model="form.brief" rows="3"
                placeholder="The angle, sources to approach, what to avoid…"></textarea>
    </label>
    <div class="row">
      <label class="grow">WRITER
        <select v-model="form.writer">
          <option value="">Select a writer…</option>
          <option v-for="w in writers" :key="w.id" :value="w.id">
            {{ w.first_name }} {{ w.last_name }}
          </option>
        </select>
      </label>
      <label>CATEGORY
        <select v-model="form.category">
          <option value="">—</option>
          <option>Business</option><option>Tech</option><option>Life</option>
          <option>Innovation</option><option>Leadership</option>
        </select>
      </label>
      <label>DEADLINE
        <input v-model="form.deadline" type="date" />
      </label>
    </div>
    <p v-if="error" class="err" role="alert">{{ error }}</p>
    <button class="primary" :disabled="busy" @click="submit">
      {{ busy ? 'Assigning…' : 'Assign to Writer' }}
    </button>
  </div>
</template>

<style scoped>
.head { display: flex; justify-content: space-between; align-items: center; margin-top: 28px; }
.head h3 { margin: 0; font-size: 15px; }
.new { border: 1px solid #ccc; background: #fff; border-radius: 6px;
       padding: 7px 14px; font-size: 13px; cursor: pointer; }
.form { border: 1px solid #e6e6e6; border-radius: 8px; padding: 16px;
        background: #fafafa; margin: 12px 0 6px; }
label { display: block; font-size: 11px; color: #555; letter-spacing: .5px; margin-bottom: 12px; }
.row { display: flex; gap: 12px; }
.row label { flex: 1; margin-bottom: 12px; }
.row label.grow { flex: 2; }
input, select, textarea { width: 100%; padding: 9px; border: 1px solid #ccc;
                          border-radius: 6px; font-size: 13px; margin-top: 5px;
                          font-family: inherit; }
textarea { resize: vertical; }
.primary { width: 100%; padding: 11px; border: 0; background: #1a2744; color: #fff;
           border-radius: 6px; font-weight: 600; cursor: pointer; }
.primary:disabled { opacity: .55; }
.err { color: #c00; font-size: 13px; }
</style>
