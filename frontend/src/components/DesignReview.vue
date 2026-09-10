<script setup>
import { ref, onMounted, computed } from 'vue'
import api from '../services/api'

const designs = ref([])
const loading = ref(true)
const busy = ref(null)
const error = ref('')

const revisingId = ref(null)
const revisionNotes = ref('')

const pending = computed(() =>
  designs.value.filter(d => d.status === 'PENDING_REVIEW'))
const settled = computed(() =>
  designs.value.filter(d => ['APPROVED', 'REVISION_REQUESTED'].includes(d.status)))

async function load() {
  const { data } = await api.get('/design/designs/')
  designs.value = data.results ?? data
  loading.value = false
}
onMounted(load)

async function approve(d) {
  error.value = ''
  busy.value = d.id
  try { await api.post(`/design/designs/${d.id}/approve/`); await load() }
  catch (e) { error.value = e.response?.data?.detail || 'Approval failed.' }
  finally { busy.value = null }
}

function startRevision(d) {
  revisingId.value = d.id
  revisionNotes.value = ''
  error.value = ''
}

async function sendRevision(d) {
  error.value = ''
  if (revisionNotes.value.trim().length < 5) {
    error.value = 'Describe the corrections needed.'
    return
  }
  busy.value = d.id
  try {
    await api.post(`/design/designs/${d.id}/request-revision/`,
                   { notes: revisionNotes.value })
    revisingId.value = null
    await load()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Request failed.'
  } finally { busy.value = null }
}

const statusLabel = {
  APPROVED: 'Approved',
  REVISION_REQUESTED: 'Revision requested',
}
</script>

<template>
  <div>
    <h3>Magazine layouts awaiting review</h3>
    <p v-if="loading">Loading…</p>
    <p v-else-if="!pending.length" class="empty">No layouts waiting.</p>

    <p v-if="error" class="err" role="alert">{{ error }}</p>

    <div v-for="d in pending" :key="d.id" class="card">
      <div class="top">
        <div class="meta">
          <span class="t">{{ d.issue_title || `Issue ${d.issue}` }} · {{ d.version }}</span>
          <em>{{ d.designer_name }} · {{ d.file_name }}</em>
        </div>
        <a :href="d.file" target="_blank" class="file">Open file</a>
      </div>

      <p v-if="d.notes_to_editor" class="dnotes">
        <b>From the designer:</b> {{ d.notes_to_editor }}
      </p>

      <div v-if="revisingId === d.id" class="composer">
        <textarea v-model="revisionNotes" rows="3"
                  placeholder="Layout, typography, imagery or branding corrections…"></textarea>
        <div class="acts">
          <button class="ghost" @click="revisingId = null">Cancel</button>
          <button class="warn" :disabled="busy === d.id" @click="sendRevision(d)">
            Send to Designer
          </button>
        </div>
      </div>
      <div v-else class="acts">
        <button class="ghost" @click="startRevision(d)">Request Revision</button>
        <button class="primary" :disabled="busy === d.id" @click="approve(d)">
          {{ busy === d.id ? 'Approving…' : 'Approve Design' }}
        </button>
      </div>
    </div>

    <template v-if="settled.length">
      <h3>Reviewed layouts</h3>
      <ul class="settled">
        <li v-for="d in settled" :key="d.id">
          <div class="meta">
            <span class="t">{{ d.issue_title || `Issue ${d.issue}` }} · {{ d.version }}</span>
            <em>{{ d.designer_name }}</em>
          </div>
          <span class="badge" :class="d.status.toLowerCase()">
            {{ statusLabel[d.status] }}
          </span>
        </li>
      </ul>
    </template>
  </div>
</template>

<style scoped>
h3 { margin: 28px 0 10px; font-size: 15px; }
.card { border: 1px solid #eee; border-radius: 8px; padding: 14px 16px; margin-bottom: 10px; }
.top { display: flex; justify-content: space-between; align-items: center; }
.meta { display: flex; flex-direction: column; gap: 3px; }
.t { font-weight: 600; font-size: 14px; }
em { font-size: 12px; color: #888; font-style: normal; }
.file { font-size: 13px; color: #4a7fb5; }
.dnotes { font-size: 13px; color: #555; margin: 12px 0 0; line-height: 1.55;
          border-left: 3px solid #eee; padding-left: 10px; }
.composer { margin-top: 12px; }
textarea { width: 100%; padding: 9px; border: 1px solid #ccc; border-radius: 6px;
           font-family: inherit; font-size: 13px; resize: vertical; }
.acts { display: flex; gap: 8px; margin-top: 12px; }
.ghost { flex: 1; padding: 10px; border: 1px solid #ccc; background: #fff;
         border-radius: 6px; cursor: pointer; font-size: 13px; }
.primary { flex: 1; padding: 10px; border: 0; background: #1a2744; color: #fff;
           border-radius: 6px; font-weight: 600; cursor: pointer; font-size: 13px; }
.warn { flex: 1; padding: 10px; border: 0; background: #b5651d; color: #fff;
        border-radius: 6px; font-weight: 600; cursor: pointer; font-size: 13px; }
button:disabled { opacity: .55; }
.settled { list-style: none; padding: 0; margin: 0; }
.settled li { display: flex; justify-content: space-between; align-items: center;
              border: 1px solid #f0f0f0; border-radius: 8px; padding: 11px 14px; margin-bottom: 7px; }
.badge { font-size: 11px; padding: 4px 10px; border-radius: 12px; }
.badge.approved { background: #eaf7f0; color: #1c6b45; }
.badge.revision_requested { background: #fdf2e0; color: #96631a; }
.empty { color: #888; font-size: 14px; }
.err { color: #c00; font-size: 13px; }
</style>
