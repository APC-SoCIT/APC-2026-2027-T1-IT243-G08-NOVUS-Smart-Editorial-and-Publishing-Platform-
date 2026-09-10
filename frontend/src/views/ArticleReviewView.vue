<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../services/api'
import EvaluationPanel from '../components/EvaluationPanel.vue'
import IssueAssign from '../components/IssueAssign.vue'
import MessageThread from '../components/MessageThread.vue'

const route = useRoute()
const router = useRouter()
const id = route.params.id

const article = ref(null)
const loading = ref(true)
const busy = ref(false)
const error = ref('')

const showComposer = ref(false)
const notes = ref([])
const overrideOpen = ref(false)
const withdrawOpen = ref(false)
const withdrawReason = ref('')
const overrideReason = ref('')

async function load() {
  const { data } = await api.get(`/editorial/articles/${id}/`)
  article.value = data
  loading.value = false
}
onMounted(load)

function startRevision() {
  // Prefill from the AI's suggestions (UC-1.7): the Editor accepts, edits, or removes.
  const s = article.value?.latest_evaluation?.suggestions || []
  notes.value = s.length
    ? s.map(x => ({ ...x }))
    : [{ section: '', note_type: 'STRUCTURE', instruction: '', priority: 'MEDIUM' }]
  showComposer.value = true
}
const addNote = () =>
  notes.value.push({ section: '', note_type: 'STRUCTURE', instruction: '', priority: 'MEDIUM' })
const removeNote = (i) => notes.value.splice(i, 1)

async function act(fn) {
  error.value = ''
  busy.value = true
  try { await fn(); router.push('/editor') }
  catch (e) { error.value = e.response?.data?.detail || 'Action failed.' }
  finally { busy.value = false }
}

const approve = () => act(() => api.post(`/editorial/articles/${id}/approve/`))

const withdraw = () => act(() => {
  if (withdrawReason.value.trim().length < 5)
    throw { response: { data: { detail: 'Give a reason for withdrawing.' } } }
  return api.post(`/editorial/articles/${id}/withdraw/`, { reason: withdrawReason.value })
})

const sendRevision = () => act(() => {
  const payload = notes.value.filter(n => n.instruction.trim())
  if (!payload.length) throw { response: { data: { detail: 'Add at least one note.' } } }
  return api.post(`/editorial/articles/${id}/request-revision/`, { notes: payload })
})

const submitOverride = () => act(() => {
  if (overrideReason.value.trim().length < 10)
    throw { response: { data: { detail: 'A justification of at least 10 characters is required.' } } }
  return api.post(`/editorial/articles/${id}/override/`, { reason: overrideReason.value })
})
</script>

<template>
  <div class="wrap" v-if="!loading && article">
    <header>
      <h2>ARTICLE REVIEW</h2>
      <router-link to="/editor" class="back">Back to dashboard</router-link>
    </header>

    <h1>{{ article.title }}</h1>
    <p class="byline">
      {{ article.writer_name }} · {{ article.category || 'Uncategorised' }} ·
      <b>{{ article.status.replace('_', ' ') }}</b>
    </p>

    <EvaluationPanel
      :evaluation="article.latest_evaluation"
      :returned-by-ai="article.returned_by_ai"
      :threshold="70" />

    <div class="body" v-html="article.body"></div>

    <div v-if="article.revision_notes?.length" class="history">
      <h5>Revision history</h5>
      <div v-for="n in article.revision_notes" :key="n.id" class="hnote">
        <span class="tag">{{ n.note_type }}</span>
        <span class="tag">{{ n.priority }}</span>
        <em>{{ n.editor_name || 'Automated pre-screening' }}</em>
        <p>{{ n.instruction }}</p>
      </div>
    </div>

    <IssueAssign
      v-if="['APPROVED', 'PUBLISHED'].includes(article.status)"
      :article-id="article.id"
      :current-issue="article.issue"
      @assigned="load" />

    <MessageThread :article-id="article.id" />

    <p v-if="error" class="err">{{ error }}</p>

    <!-- Revision composer -->
    <div v-if="showComposer" class="composer">
      <h5>Revision notes</h5>
      <p class="hint" v-if="article.latest_evaluation?.suggestions?.length">
        Prefilled from the automated evaluation. Edit or remove anything you disagree with.
      </p>
      <div v-for="(n, i) in notes" :key="i" class="note-row">
        <div class="row">
          <input v-model="n.section" placeholder="Section" />
          <select v-model="n.note_type">
            <option>GRAMMAR</option><option>TONE</option>
            <option>STRUCTURE</option><option>FACTUAL</option>
          </select>
          <select v-model="n.priority">
            <option>LOW</option><option>MEDIUM</option><option>HIGH</option>
          </select>
          <button class="x" @click="removeNote(i)">×</button>
        </div>
        <textarea v-model="n.instruction" rows="2"
                  placeholder="Specific instruction for the writer…"></textarea>
      </div>
      <button class="ghost sm" @click="addNote">+ Add another note</button>
    </div>

    <div v-if="withdrawOpen" class="composer">
      <h5>Withdraw this article</h5>
      <p class="hint">
        It leaves the active pipeline and is removed from any issue it belongs to.
      </p>
      <textarea v-model="withdrawReason" rows="2"
                placeholder="Why is this being withdrawn?"></textarea>
    </div>

    <!-- Override -->
    <div v-if="overrideOpen" class="composer">
      <h5>Override justification</h5>
      <p class="hint">Recorded against this evaluation for audit and reporting.</p>
      <textarea v-model="overrideReason" rows="3"
                placeholder="Why are you setting aside the automated verdict?"></textarea>
    </div>

    <div class="actions">
      <template v-if="showComposer">
        <button class="ghost" @click="showComposer = false">Cancel</button>
        <button class="warn" :disabled="busy" @click="sendRevision">Send to Writer</button>
      </template>
      <template v-else-if="overrideOpen">
        <button class="ghost" @click="overrideOpen = false">Cancel</button>
        <button class="primary" :disabled="busy" @click="submitOverride">
          Override and Approve
        </button>
      </template>
      <template v-else-if="withdrawOpen">
        <button class="ghost" @click="withdrawOpen = false">Cancel</button>
        <button class="warn" :disabled="busy" @click="withdraw">Confirm Withdrawal</button>
      </template>
      <template v-else>
        <button class="ghost" @click="withdrawOpen = true">Withdraw</button>
        <button class="ghost" @click="startRevision">Request Revisions</button>
        <button v-if="article.latest_evaluation" class="ghost" @click="overrideOpen = true">
          Override AI
        </button>
        <button class="primary" :disabled="busy" @click="approve">Approve</button>
      </template>
    </div>
  </div>
  <p v-else class="wrap">Loading…</p>
</template>

<style scoped>
.wrap { max-width: 820px; margin: 40px auto; font-family: system-ui; padding: 0 16px 60px; }
header { display: flex; justify-content: space-between; align-items: center; }
h2 { margin: 0; letter-spacing: 1px; font-size: 16px; }
.back { font-size: 13px; color: #555; }
h1 { margin: 18px 0 4px; font-size: 27px; line-height: 1.25; }
.byline { margin: 0 0 20px; font-size: 13px; color: #777; }
.body { border: 1px solid #eee; border-radius: 8px; padding: 20px; line-height: 1.7; background: #fff; }
.body :deep(h2) { font-size: 20px; margin: 18px 0 8px; }
.body :deep(p) { margin: 0 0 12px; }
.history { margin-top: 24px; }
.history h5, .composer h5 { margin: 0 0 8px; font-size: 12px; letter-spacing: .5px;
                            text-transform: uppercase; color: #555; }
.hnote { border-top: 1px solid #eee; padding: 10px 0; }
.hnote em { font-size: 11px; color: #888; font-style: normal; margin-left: 6px; }
.hnote p { margin: 5px 0 0; font-size: 13px; }
.tag { font-size: 10px; padding: 2px 7px; border-radius: 10px; background: #eef2f7; color: #445; margin-right: 4px; }
.composer { margin-top: 24px; border: 1px solid #e0e0e0; border-radius: 8px; padding: 16px; background: #fafafa; }
.hint { margin: 0 0 12px; font-size: 12px; color: #888; }
.note-row { margin-bottom: 12px; }
.row { display: flex; gap: 6px; margin-bottom: 6px; }
.row input, .row select { padding: 7px; border: 1px solid #ccc; border-radius: 5px; font-size: 13px; }
.row input { flex: 1; }
.x { border: 1px solid #ccc; background: #fff; border-radius: 5px; width: 30px; cursor: pointer; }
textarea { width: 100%; padding: 9px; border: 1px solid #ccc; border-radius: 5px;
           font-family: inherit; font-size: 13px; resize: vertical; }
.actions { display: flex; gap: 10px; margin-top: 24px; }
.ghost { flex: 1; padding: 12px; border: 1px solid #ccc; background: #fff; border-radius: 6px; cursor: pointer; }
.ghost.sm { flex: none; padding: 7px 12px; font-size: 13px; }
.primary { flex: 1; padding: 12px; border: 0; background: #1a2744; color: #fff;
           border-radius: 6px; font-weight: 600; cursor: pointer; }
.warn { flex: 1; padding: 12px; border: 0; background: #b5651d; color: #fff;
        border-radius: 6px; font-weight: 600; cursor: pointer; }
button:disabled { opacity: .55; }
.err { color: #c00; font-size: 13px; margin-top: 14px; }
</style>
