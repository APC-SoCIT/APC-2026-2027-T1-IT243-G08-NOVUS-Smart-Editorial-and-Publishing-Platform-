<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import api from '../services/api'
import { useAuthStore } from '../stores/auth'
import StaffLayout from '../components/StaffLayout.vue'
import SlideOver from '../components/SlideOver.vue'
import UiBadge from '../components/ui/UiBadge.vue'
import UiEmpty from '../components/ui/UiEmpty.vue'
import UiSkeleton from '../components/ui/UiSkeleton.vue'
import UiButton from '../components/ui/UiButton.vue'

const auth = useAuthStore()
const router = useRouter()

const designs = ref([])
const articles = ref([])
const issues = ref([])
const loading = ref(true)
const tab = ref('copy')

const uploadOpen = ref(false)
const issueId = ref('')
const version = ref('v1.0')
const notes = ref('')
const file = ref(null)
const uploading = ref(false)
const error = ref('')
const ok = ref('')

const current = computed(() => designs.value.filter(d => d.status !== 'SUPERSEDED'))
const history = computed(() => designs.value.filter(d => d.status === 'SUPERSEDED'))
const needsWork = computed(() =>
  designs.value.filter(d => d.status === 'REVISION_REQUESTED'))
const awaiting = computed(() =>
  designs.value.filter(d => d.status === 'PENDING_REVIEW'))

const TABS = computed(() => [
  { key: 'copy',    label: 'Ready for layout', count: articles.value.length },
  { key: 'mine',    label: 'My layouts',       count: current.value.length },
  { key: 'history', label: 'Earlier versions', count: history.value.length },
])

async function load() {
  const [d, a, i] = await Promise.all([
    api.get('/design/designs/'),
    api.get('/editorial/articles/'),
    api.get('/publication/issues/'),
  ])
  designs.value = d.data.results ?? d.data
  articles.value = (a.data.results ?? a.data)
    .filter(x => ['APPROVED', 'PUBLISHED'].includes(x.status))
  issues.value = (i.data.results ?? i.data)
    .filter(x => !['PUBLISHED', 'ARCHIVED'].includes(x.status))
  if (!issueId.value && issues.value.length) issueId.value = issues.value[0].id
}

onMounted(async () => {
  try {
    if (!auth.user) await auth.fetchUser()
    await load()
  } finally { loading.value = false }
})

function pick(e) { file.value = e.target.files[0] || null }

async function upload() {
  error.value = ''; ok.value = ''
  if (!issueId.value) { error.value = 'Choose the issue this layout is for.'; return }
  if (!file.value) { error.value = 'Choose a layout file.'; return }

  uploading.value = true
  const fd = new FormData()
  fd.append('issue', issueId.value)
  fd.append('version', version.value)
  fd.append('notes_to_editor', notes.value)
  fd.append('file', file.value)
  try {
    await api.post('/design/designs/', fd,
      { headers: { 'Content-Type': 'multipart/form-data' } })
    file.value = null; notes.value = ''
    uploadOpen.value = false
    tab.value = 'mine'
    await load()
  } catch (e) {
    const d = e.response?.data
    error.value = d?.file?.[0] || d?.non_field_errors?.[0] || 'Upload failed.'
  } finally { uploading.value = false }
}

const photos = (a) => a.image_count || 0
</script>

<template>
  <StaffLayout title="Designer workspace" subtitle="Approved copy and magazine layouts">

    <template #action>
      <UiButton variant="primary" @click="uploadOpen = true">
        + Upload layout
      </UiButton>
    </template>

    <div v-if="needsWork.length" class="alert" role="status">
      <b>{{ needsWork[0].issue_title }} — {{ needsWork[0].version }}
        needs revision.</b>
      <span>{{ needsWork[0].revision_notes }}</span>
      <UiButton variant="warn" size="sm" @click="uploadOpen = true">
        Upload a new version
      </UiButton>
    </div>

    <div class="toolbar">
      <nav class="tabs" role="tablist" aria-label="Designer views">
        <button v-for="t in TABS" :key="t.key" role="tab"
                :aria-selected="tab === t.key" :class="{ on: tab === t.key }"
                @click="tab = t.key">
          {{ t.label }}<span class="count">{{ t.count }}</span>
        </button>
      </nav>
    </div>

    <UiSkeleton v-if="loading" :rows="4" label="Loading your workspace" />

    <!-- approved copy -->
    <template v-else-if="tab === 'copy'">
      <UiEmpty v-if="!articles.length" icon="○" title="No approved copy yet"
               body="Articles appear here once an editor approves them, ready to be laid out." />
      <ul v-else class="rows">
        <li v-for="a in articles" :key="a.id" class="row" tabindex="0" role="button"
            @click="router.push(`/designer/article/${a.id}`)"
            @keyup.enter="router.push(`/designer/article/${a.id}`)">
          <div class="meta">
            <span class="t">{{ a.title }}</span>
            <span class="sub">
              {{ a.writer_name }} · {{ a.category || 'Uncategorised' }}
              · {{ a.reading_time }} min read
            </span>
          </div>
          <span class="photos">{{ photos(a) }} photo{{ photos(a) === 1 ? '' : 's' }}</span>
          <span class="go" aria-hidden="true">→</span>
        </li>
      </ul>
    </template>

    <!-- my layouts -->
    <template v-else-if="tab === 'mine'">
      <UiEmpty v-if="!current.length" icon="□" title="No layouts submitted"
               body="Upload a layout and it goes to an editor for review.">
        <template #action>
          <UiButton variant="primary" @click="uploadOpen = true">Upload a layout</UiButton>
        </template>
      </UiEmpty>
      <ul v-else class="rows">
        <li v-for="d in current" :key="d.id" class="row">
          <div class="meta">
            <span class="t">{{ d.issue_title }} · {{ d.version }}</span>
            <span class="sub">{{ d.file_name }}</span>
            <p v-if="d.revision_notes" class="notes">{{ d.revision_notes }}</p>
          </div>
          <UiBadge :status="d.status" />
          <a v-if="d.file" :href="d.file" target="_blank" class="open"
             :aria-label="`Open ${d.file_name}`">Open</a>
        </li>
      </ul>
    </template>

    <!-- superseded -->
    <template v-else>
      <UiEmpty v-if="!history.length" icon="↩" title="No earlier versions"
               body="When you upload a replacement, the previous version is kept here." />
      <ul v-else class="rows">
        <li v-for="d in history" :key="d.id" class="row dim">
          <div class="meta">
            <span class="t">{{ d.issue_title }} · {{ d.version }}</span>
            <span class="sub">{{ d.file_name }}</span>
          </div>
          <UiBadge :status="d.status" />
        </li>
      </ul>
    </template>

    <template #rail>
      <div class="glance">
        <h2>At a glance</h2>
        <dl>
          <div><dt>Copy to lay out</dt><dd>{{ articles.length }}</dd></div>
          <div><dt>With the editor</dt><dd>{{ awaiting.length }}</dd></div>
          <div :class="{ warn: needsWork.length }">
            <dt>Needs revision</dt><dd>{{ needsWork.length }}</dd>
          </div>
          <div><dt>Open issues</dt><dd>{{ issues.length }}</dd></div>
        </dl>
      </div>
    </template>
  </StaffLayout>

  <SlideOver :open="uploadOpen" title="Upload a layout"
             subtitle="Submit a magazine layout for editor review."
             @close="uploadOpen = false">
    <label>ISSUE
      <select v-model="issueId">
        <option value="">Select an issue…</option>
        <option v-for="i in issues" :key="i.id" :value="i.id">
          Issue {{ i.number }} — {{ i.title }}
        </option>
      </select>
    </label>

    <label>VERSION
      <input v-model="version" placeholder="v1.0" />
    </label>

    <label>LAYOUT FILE
      <input type="file" accept=".pdf,.indd,.ai,.psd,.png,.jpg,.jpeg"
             @change="pick" />
    </label>
    <p class="hint">
      PDF, INDD, AI, PSD or image, up to 100 MB. A PDF can be read in the
      browser by subscribers; other formats download only.
    </p>

    <label>NOTES TO EDITOR
      <textarea v-model="notes" rows="3"
                placeholder="Anything the editor should know about this version"></textarea>
    </label>

    <p v-if="error" class="ferr" role="alert">{{ error }}</p>
    <UiButton variant="primary" full :loading="uploading" @click="upload">
      Submit for editor review
    </UiButton>
  </SlideOver>
</template>

<style scoped>
.alert { display: flex; align-items: center; gap: var(--s-4); flex-wrap: wrap;
         background: var(--warn-bg); border: 1px solid var(--warn-line);
         border-radius: var(--r-md); padding: var(--s-4) var(--s-5);
         margin-bottom: var(--s-5); font-size: 15px; color: var(--warn); }
.alert span { flex: 1; color: #7a5a2a; }

.toolbar { margin-bottom: var(--s-5); }
.tabs { display: flex; gap: var(--s-1); }
.tabs button { display: inline-flex; align-items: center; gap: 8px;
               background: none; border: 0; border-radius: var(--r-sm);
               padding: 10px 16px; font-size: 15px; font-weight: 500;
               color: var(--nv-text-muted); cursor: pointer;
               transition: background var(--dur-fast) var(--ease-out); }
.tabs button:hover { background: #eef0f3; color: var(--nv-text); }
.tabs button.on { background: var(--nv-navy-2); color: #fff; font-weight: 600; }
.count { font-size: 13px; font-weight: 700; padding: 1px 8px;
         border-radius: var(--r-full); background: #e4e7ec; color: var(--nv-text-muted); }
.tabs button.on .count { background: rgba(255,255,255,.22); color: #fff; }

.rows { list-style: none; margin: 0; padding: 0;
        display: flex; flex-direction: column; gap: 8px; }
.row { display: flex; align-items: center; gap: var(--s-4);
       padding: 14px 18px; background: var(--nv-surface);
       border: 1px solid var(--nv-line); border-radius: var(--r-md);
       transition: border-color var(--dur-fast) var(--ease-out),
                   box-shadow var(--dur-fast) var(--ease-out); }
.row[role="button"] { cursor: pointer; }
.row[role="button"]:hover { border-color: var(--nv-line-strong);
                            box-shadow: var(--shadow-sm); }
.row.dim { opacity: .6; }

.meta { flex: 1; min-width: 0; }
.t { display: block; font-size: 16px; font-weight: 600; color: var(--nv-text);
     line-height: 1.35; margin-bottom: 3px; }
.sub { font-size: 14px; color: var(--nv-text-muted); }
.notes { margin: 8px 0 0; font-size: 14px; line-height: 1.55; color: var(--warn);
         padding-left: 12px; border-left: 2px solid var(--warn-line); }

.photos { font-size: 14px; color: var(--nv-text-muted); white-space: nowrap; }
.go { color: var(--nv-text-faint); font-size: 18px; }
.open { font-size: 14px; color: var(--nv-accent); }

.glance { background: var(--nv-surface); border: 1px solid var(--nv-line);
          border-radius: var(--r-md); padding: var(--s-5); }
.glance h2 { font-size: 13px; letter-spacing: .06em; text-transform: uppercase;
             color: var(--nv-text-faint); margin: 0 0 var(--s-4); font-weight: 600; }
dl { margin: 0; }
dl > div { display: flex; justify-content: space-between; align-items: baseline;
           padding: 10px 0; border-bottom: 1px solid var(--nv-line); }
dl > div:last-child { border-bottom: 0; }
dt { font-size: 14px; color: var(--nv-text-muted); }
dd { margin: 0; font-size: 20px; font-weight: 700; color: var(--nv-text);
     font-variant-numeric: tabular-nums; }
dl > div.warn dd { color: var(--warn); }

label { display: block; font-size: 13px; color: var(--nv-text-muted);
        letter-spacing: .04em; margin-bottom: 16px; }
label input, label select, label textarea {
  width: 100%; margin-top: 6px; padding: 11px 13px; font-size: 15px;
  border: 1px solid var(--nv-line-strong); border-radius: var(--r-sm);
  font-family: inherit; }
textarea { resize: vertical; }
.hint { font-size: 14px; color: var(--nv-text-muted); line-height: 1.6;
        margin: -8px 0 16px; }
.ferr { color: var(--bad); font-size: 14px; margin: 0 0 var(--s-3); }
</style>
