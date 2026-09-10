<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import api from '../services/api'
import { useAuthStore } from '../stores/auth'
import NotificationBell from '../components/NotificationBell.vue'

const auth = useAuthStore()
const router = useRouter()

const designs = ref([])
const approvedArticles = ref([])
const loading = ref(true)
const error = ref('')
const ok = ref('')

const issues = ref([])
const issueId = ref('')
const version = ref('v1.0')
const notes = ref('')
const file = ref(null)
const uploading = ref(false)

const current = computed(() =>
  designs.value.filter(d => d.status !== 'SUPERSEDED'))
const history = computed(() =>
  designs.value.filter(d => d.status === 'SUPERSEDED'))
const needsRevision = computed(() =>
  designs.value.find(d => d.status === 'REVISION_REQUESTED'))

async function load() {
  const [d, a, i] = await Promise.all([
    api.get('/design/designs/'),
    api.get('/editorial/articles/'),
    api.get('/publication/issues/'),
  ])
  issues.value = (i.data.results ?? i.data)
    .filter(x => !['PUBLISHED', 'ARCHIVED'].includes(x.status))
  if (!issueId.value && issues.value.length) issueId.value = issues.value[0].id
  designs.value = d.data.results ?? d.data
  approvedArticles.value = (a.data.results ?? a.data)
    .filter(x => ['APPROVED', 'PUBLISHED'].includes(x.status))
  loading.value = false
}

onMounted(async () => {
  if (!auth.user) await auth.fetchUser()
  await load()
})

function pick(e) { file.value = e.target.files[0] || null }

async function upload() {
  error.value = ''; ok.value = ''
  if (!issueId.value) { error.value = 'Choose the issue this layout is for.'; return }
  if (!file.value) { error.value = 'Choose a layout file first.'; return }
  uploading.value = true
  const fd = new FormData()
  fd.append('issue', issueId.value)
  fd.append('version', version.value)
  fd.append('notes_to_editor', notes.value)
  fd.append('file', file.value)
  try {
    await api.post('/design/designs/', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    ok.value = 'Layout submitted for editor review.'
    file.value = null; notes.value = ''
    document.getElementById('layout-file').value = ''
    await load()
  } catch (e) {
    const d = e.response?.data
    error.value = d?.file?.[0] || d?.non_field_errors?.[0] || d?.detail || 'Upload failed.'
  } finally { uploading.value = false }
}

function signOut() { auth.logout(); router.push('/staff/login') }

const statusLabel = {
  PENDING_REVIEW: 'Pending editor review',
  APPROVED: 'Approved',
  REVISION_REQUESTED: 'Revision requested',
  SUPERSEDED: 'Superseded',
}
</script>

<template>
  <div class="wrap">
    <header>
      <h2>DESIGNER WORKSPACE</h2>
      <div class="hactions">
        <NotificationBell />
        <button class="out" @click="signOut">Sign out</button>
      </div>
    </header>
    <p class="hi">Welcome back, {{ auth.user?.first_name }}!</p>

    <div v-if="needsRevision" class="alert">
      <b>Revision requested on {{ needsRevision.version }}</b>
      <p>{{ needsRevision.revision_notes }}</p>
      <small>Upload a corrected version below — the previous one is kept.</small>
    </div>

    <h3>Approved articles ready for layout</h3>
    <p v-if="loading">Loading…</p>
    <p v-else-if="!approvedArticles.length" class="empty">
      Nothing approved yet.
    </p>
    <ul v-else class="arts">
      <li v-for="a in approvedArticles" :key="a.id"
          @click="router.push(`/designer/article/${a.id}`)">
        <div class="meta">
          <span class="t">{{ a.title }}</span>
          <em>{{ a.writer_name }} · {{ a.category || 'Uncategorised' }}</em>
        </div>
        <span class="open">Open for layout →</span>
      </li>
    </ul>

    <h3>Submit a layout</h3>
    <div class="form">
      <div class="row">
        <label class="grow">ISSUE
          <select v-model="issueId">
            <option value="">Select an issue…</option>
            <option v-for="i in issues" :key="i.id" :value="i.id">
              Issue #{{ i.number }} — {{ i.title }}
            </option>
          </select>
        </label>
        <label>VERSION
          <input v-model="version" placeholder="v1.0" />
        </label>
      </div>
      <label>LAYOUT FILE
        <input id="layout-file" type="file" @change="pick"
               accept=".pdf,.indd,.ai,.psd,.png,.jpg,.jpeg" />
      </label>
      <small class="hint">PDF, INDD, AI, PSD or image. Max 100 MB.</small>
      <label>NOTES TO EDITOR
        <textarea v-model="notes" rows="3" placeholder="Anything the editor should know…"></textarea>
      </label>
      <p v-if="error" class="err">{{ error }}</p>
      <p v-if="ok" class="ok">{{ ok }}</p>
      <button class="primary" :disabled="uploading" @click="upload">
        {{ uploading ? 'Uploading…' : 'Submit Layout for Editor Review' }}
      </button>
    </div>

    <h3>My submissions</h3>
    <p v-if="!current.length" class="empty">No layouts submitted yet.</p>
    <ul v-else class="designs">
      <li v-for="d in current" :key="d.id">
        <div class="meta">
          <span class="t">{{ d.issue_title || `Issue ${d.issue}` }} · {{ d.version }}</span>
          <em>{{ d.file_name }}</em>
        </div>
        <span class="badge" :class="d.status.toLowerCase()">{{ statusLabel[d.status] }}</span>
      </li>
    </ul>

    <template v-if="history.length">
      <h3>Earlier versions</h3>
      <ul class="designs">
        <li v-for="d in history" :key="d.id" class="dim">
          <div class="meta">
            <span class="t">{{ d.issue_title || `Issue ${d.issue}` }} · {{ d.version }}</span>
            <em>{{ d.file_name }}</em>
          </div>
          <span class="badge superseded">Superseded</span>
        </li>
      </ul>
    </template>
  </div>
</template>

<style scoped>
.wrap { max-width: 780px; margin: 40px auto; font-family: system-ui; padding: 0 16px 60px; }
header { display: flex; justify-content: space-between; align-items: center; }
h2 { margin: 0; letter-spacing: 1px; }
.hactions { display: flex; gap: 10px; align-items: center; }
.out { border: 1px solid #ccc; background: #fff; border-radius: 6px; padding: 6px 12px; cursor: pointer; }
.hi { color: #555; }
h3 { margin: 30px 0 10px; font-size: 15px; }
.alert { background: #fff8ee; border: 1px solid #f0d9b5; border-radius: 8px;
         padding: 14px 16px; margin-top: 18px; }
.alert b { font-size: 14px; color: #96631a; }
.alert p { margin: 6px 0; font-size: 13px; line-height: 1.55; }
.alert small { font-size: 12px; color: #888; }
ul { list-style: none; padding: 0; margin: 0; }
.arts li { border-bottom: 1px solid #eee; padding: 12px 0; display: flex;
           justify-content: space-between; align-items: center; cursor: pointer; }
.arts li:hover { background: #fafafa; }
.open { font-size: 12px; color: #4a7fb5; }
.designs li { display: flex; justify-content: space-between; align-items: center;
              border: 1px solid #eee; border-radius: 8px; padding: 12px 14px; margin-bottom: 8px; }
.designs li.dim { opacity: .55; }
.meta { display: flex; flex-direction: column; gap: 3px; }
.t { font-weight: 600; font-size: 14px; }
em { font-size: 12px; color: #888; font-style: normal; }
.badge { font-size: 11px; padding: 4px 10px; border-radius: 12px; background: #eef2f7; color: #445; }
.badge.pending_review { background: #eaf1fb; color: #2b5a8f; }
.badge.approved { background: #eaf7f0; color: #1c6b45; }
.badge.revision_requested { background: #fdf2e0; color: #96631a; }
.badge.superseded { background: #f2f2f2; color: #888; }
.form { border: 1px solid #e6e6e6; border-radius: 8px; padding: 16px; background: #fafafa; }
.form label { display: block; font-size: 11px; color: #555; letter-spacing: .5px; margin-bottom: 12px; }
.row { display: flex; gap: 12px; }
.row label { flex: 1; }
.row label.grow { flex: 2; }
select { width: 100%; padding: 9px; border: 1px solid #ccc; border-radius: 6px;
         font-size: 13px; margin-top: 5px; }
input, textarea { width: 100%; padding: 9px; border: 1px solid #ccc; border-radius: 6px;
                  font-family: inherit; font-size: 13px; margin-top: 5px; }
.hint { display: block; font-size: 11px; color: #999; margin: -6px 0 12px; }
.primary { width: 100%; padding: 12px; border: 0; background: #1a2744; color: #fff;
           border-radius: 6px; font-weight: 600; cursor: pointer; }
.primary:disabled { opacity: .55; }
.err { color: #c00; font-size: 13px; }
.ok { color: #0a7; font-size: 13px; }
.empty { color: #888; font-size: 14px; }
</style>
